from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from youtube_suite.config.settings import get_settings
from youtube_suite.infrastructure.persistence.app_models import AppJob

logger = logging.getLogger(__name__)


def run_shorts_pipeline(
    session: Session,
    job_id: uuid.UUID,
    video_path: Path,
    language: str = "es",
    generate_vertical: bool = False,
    generate_titles: bool = False,
) -> None:
    """Execute the podcast→shorts pipeline and persist result_json on app.jobs."""
    from youtube_suite.infrastructure.ml.shorts.audio_service import extract_audio, get_audio_duration
    from youtube_suite.infrastructure.ml.shorts.diarization_service import (
        assign_speakers_to_segments,
        diarize_audio,
    )
    from youtube_suite.infrastructure.ml.shorts.highlights_service import (
        generate_candidate_segments,
        score_candidates,
        select_top_clips,
    )
    from youtube_suite.infrastructure.ml.shorts.transcription_service import transcribe_with_whisperx
    from youtube_suite.infrastructure.ml.shorts.video_service import extract_multiple_clips

    s = get_settings()
    audio_dir = s.cip_data_dir / "audio"
    clips_root = s.cip_data_dir / "clips"
    audio_dir.mkdir(parents=True, exist_ok=True)
    clips_root.mkdir(parents=True, exist_ok=True)

    job = session.get(AppJob, job_id)
    if job is None:
        raise ValueError("job not found")

    def _update(status: str, progress: float, message: str | None = None, err: str | None = None) -> None:
        job.status = status
        job.progress = progress
        job.message = message
        job.error = err
        job.updated_at = datetime.now(timezone.utc)
        session.commit()

    t0 = time.perf_counter()
    try:
        _update("processing", 0.05, "Extrayendo audio…")
        audio_path = audio_dir / f"{job_id}.wav"
        extract_audio(str(video_path), str(audio_path))
        audio_duration = get_audio_duration(str(audio_path))
        logger.info("[%s] Audio extracted (duration=%.1fs)", job_id, audio_duration)

        _update("processing", 0.15, "Transcribiendo…")
        t_step = time.perf_counter()
        transcription_result = transcribe_with_whisperx(str(audio_path), language=language)
        detected_lang = transcription_result.get("language", language)
        logger.info("[%s] Transcription done (%.1fs, %d segs, lang=%s)",
                    job_id, time.perf_counter() - t_step, len(transcription_result["segments"]), detected_lang)

        _update("processing", 0.30, "Diarización…")
        t_step = time.perf_counter()
        diarization_segments = diarize_audio(str(audio_path))
        transcription_segments = assign_speakers_to_segments(
            transcription_result["segments"], diarization_segments
        )
        transcription_result["segments"] = transcription_segments
        logger.info("[%s] Diarization done (%.1fs)", job_id, time.perf_counter() - t_step)

        _update("processing", 0.45, "Segmentación semántica…")
        candidates = generate_candidate_segments(transcription_segments)

        _update("processing", 0.55, "Scoring (ShortabilityScorer + hooks)…")
        t_step = time.perf_counter()
        scored = score_candidates(
            candidates,
            transcription_result["full_text"],
            audio_path=str(audio_path),
            audio_duration=audio_duration,
            language=detected_lang,
        )
        top_clips = select_top_clips(scored)
        logger.info("[%s] Scoring done (%.1fs) — %d clips from %d candidates",
                    job_id, time.perf_counter() - t_step, len(top_clips), len(candidates))

        _update("processing", 0.70, "Extrayendo clips…")
        t_step = time.perf_counter()
        clips_dir = clips_root / str(job_id)
        clips_dir.mkdir(parents=True, exist_ok=True)
        extracted = extract_multiple_clips(
            str(video_path),
            top_clips,
            str(clips_dir),
            base_filename="clip",
            generate_vertical=generate_vertical,
        )
        logger.info("[%s] Clips extracted (%.1fs)", job_id, time.perf_counter() - t_step)

        # Optionally generate titles via LLM
        if generate_titles and s.anthropic_api_key:
            _update("processing", 0.85, "Generando títulos (LLM)…")
            from youtube_suite.infrastructure.nlp.clip_titler import generate_clip_title

            for clip in extracted:
                try:
                    title_data = generate_clip_title(
                        clip["text"],
                        language=detected_lang,
                        hook_type=clip.get("hook_type"),
                    )
                    clip["title"] = title_data["title"]
                    clip["hashtags"] = title_data["hashtags"]
                except Exception as e:
                    logger.warning("[%s] Title generation failed for clip: %s", job_id, e)
                    clip.setdefault("title", None)
                    clip.setdefault("hashtags", [])
        else:
            for clip in extracted:
                clip.setdefault("title", None)
                clip.setdefault("hashtags", [])

        clips_info = []
        for i, clip in enumerate(extracted):
            clips_info.append({
                "clip_id": f"clip_{i + 1:03d}",
                "start": clip["start"],
                "end": clip["end"],
                "duration": clip["end"] - clip["start"],
                "text": clip["text"],
                "speaker": clip.get("speaker"),
                "score": clip["score"],
                "score_breakdown": clip.get("score_breakdown"),
                "hook_type": clip.get("hook_type"),
                "title": clip.get("title"),
                "hashtags": clip.get("hashtags", []),
                "path": clip["path"],
                "filename": clip["filename"],
                "vertical_path": clip.get("vertical_path"),
                "vertical_filename": clip.get("vertical_filename"),
            })

        result = {
            "transcription": {
                "full_text": transcription_result["full_text"],
                "segments": transcription_result["segments"],
                "language": detected_lang,
                "duration": transcription_result.get("duration", audio_duration),
            },
            "clips": clips_info,
            "audio_duration": audio_duration,
        }
        job.result_json = result
        job.status = "completed"
        job.progress = 1.0
        job.message = f"Completado: {len(clips_info)} clips"
        job.updated_at = datetime.now(timezone.utc)
        session.commit()
        logger.info("[%s] Shorts pipeline COMPLETED — %d clips, elapsed=%.1fs",
                    job_id, len(clips_info), time.perf_counter() - t0)

    except Exception as e:
        elapsed = time.perf_counter() - t0
        logger.exception("[%s] Shorts pipeline FAILED after %.1fs: %s", job_id, elapsed, e)
        _update("failed", 0.0, err=str(e))


def create_shorts_job(session: Session, studio_asset_id: uuid.UUID | None, video_path: Path) -> uuid.UUID:
    """Create and persist an app.jobs record for a new shorts generation job."""
    jid = uuid.uuid4()
    job = AppJob(
        id=jid,
        job_type="shorts_generation",
        status="uploaded",
        progress=0.0,
        payload_json={"video_path": str(video_path)},
        studio_asset_id=studio_asset_id,
    )
    session.add(job)
    session.commit()
    return jid
