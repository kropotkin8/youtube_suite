from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from youtube_suite.config.settings import get_settings
from youtube_suite.infrastructure.persistence.app_models import AppJob

logger = logging.getLogger(__name__)


def run_shorts_pipeline(session: Session, job_id: uuid.UUID, video_path: Path) -> None:
    """Execute podcast→shorts pipeline and persist result_json on app.jobs."""
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

    try:
        _update("processing", 0.1, "Extrayendo audio…")
        audio_path = audio_dir / f"{job_id}.wav"
        extract_audio(str(video_path), str(audio_path))
        audio_duration = get_audio_duration(str(audio_path))

        _update("processing", 0.2, "Transcribiendo…")
        transcription_result = transcribe_with_whisperx(str(audio_path), language="es")

        _update("processing", 0.4, "Diarización…")
        diarization_segments = diarize_audio(str(audio_path))
        transcription_segments = assign_speakers_to_segments(
            transcription_result["segments"],
            diarization_segments,
        )
        transcription_result["segments"] = transcription_segments

        _update("processing", 0.6, "Highlights…")
        candidates = generate_candidate_segments(transcription_segments)
        scored = score_candidates(candidates, transcription_result["full_text"])
        top_clips = select_top_clips(scored)

        _update("processing", 0.8, "Extrayendo clips…")
        clips_dir = clips_root / str(job_id)
        clips_dir.mkdir(parents=True, exist_ok=True)
        extracted = extract_multiple_clips(str(video_path), top_clips, str(clips_dir), base_filename="clip")

        clips_info = []
        for i, clip in enumerate(extracted):
            clips_info.append(
                {
                    "clip_id": f"clip_{i + 1:03d}",
                    "start": clip["start"],
                    "end": clip["end"],
                    "duration": clip["end"] - clip["start"],
                    "text": clip["text"],
                    "speaker": clip.get("speaker"),
                    "score": clip["score"],
                    "path": clip["path"],
                    "filename": clip["filename"],
                }
            )

        result = {
            "transcription": {
                "full_text": transcription_result["full_text"],
                "segments": transcription_result["segments"],
                "language": transcription_result.get("language", "es"),
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
    except Exception as e:
        logger.exception("shorts pipeline failed")
        _update("failed", 0.0, err=str(e))


def create_shorts_job(session: Session, studio_asset_id: uuid.UUID | None, video_path: Path) -> uuid.UUID:
    """Create and persist an ``app.jobs`` record for a new shorts generation job.

    Args:
        session: Active SQLAlchemy session.
        studio_asset_id: Optional linked studio media asset UUID.
        video_path: Path to the source video file.

    Returns:
        UUID of the newly created job.
    """
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
