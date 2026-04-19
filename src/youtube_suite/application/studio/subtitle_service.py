from __future__ import annotations

import logging
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from youtube_suite.application.insights.trending_service import get_trending_keywords
from youtube_suite.config.settings import get_settings
from youtube_suite.domain.ports import ASRSegment
from youtube_suite.infrastructure.media.audio_chunker import split_audio_into_chunks
from youtube_suite.infrastructure.media.subtitle_embedder import embed_subtitles
from youtube_suite.infrastructure.media.subtitle_generator import TranscriptSegment, segments_to_srt
from youtube_suite.infrastructure.ml.faster_whisper_transcriber import FasterWhisperTranscriber
from youtube_suite.infrastructure.nlp.description_generator import generate_video_description
from youtube_suite.infrastructure.nlp.local_description_generator import generate_video_description_local
from youtube_suite.infrastructure.persistence.app_models import AppJob
from youtube_suite.infrastructure.persistence.studio_models import (
    StudioGeneratedDescription,
    StudioMediaAsset,
    StudioSubtitleArtifact,
    StudioTranscriptSegment,
)

logger = logging.getLogger(__name__)


def _update_job(
    session: Session,
    job: AppJob,
    status: str,
    progress: float,
    message: str | None = None,
    error: str | None = None,
) -> None:
    job.status = status
    job.progress = progress
    job.message = message
    job.error = error
    job.updated_at = datetime.now(timezone.utc)
    session.commit()


def _purge_existing_artifacts(session: Session, asset_id: uuid.UUID) -> None:
    session.execute(delete(StudioTranscriptSegment).where(StudioTranscriptSegment.asset_id == asset_id))
    session.execute(delete(StudioSubtitleArtifact).where(StudioSubtitleArtifact.asset_id == asset_id))
    session.commit()


def create_subtitle_job(
    session: Session,
    asset_id: uuid.UUID,
    video_path: Path,
    payload: dict,
) -> uuid.UUID:
    """Create and persist an ``app.jobs`` record for a subtitle pipeline job."""
    job = AppJob(
        job_type="subtitle_pipeline",
        status="pending",
        progress=0.0,
        payload_json={"video_path": str(video_path), **payload},
        studio_asset_id=asset_id,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job.id


def create_description_job(session: Session, asset_id: uuid.UUID) -> uuid.UUID:
    """Create and persist an ``app.jobs`` record for a description generation job."""
    job = AppJob(
        job_type="description_generation",
        status="pending",
        progress=0.0,
        studio_asset_id=asset_id,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job.id


class StudioSubtitleService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def run_subtitle_pipeline_chunked(
        self,
        video_path: Path,
        asset_id: uuid.UUID,
        job_id: uuid.UUID,
        model_size: str = "medium",
        language: str = "es",
        chunk_minutes: int = 10,
        overlap_seconds: int = 5,
        output_video_path: Path | None = None,
    ) -> None:
        """Run the subtitle pipeline with chunked audio to avoid OOM on long videos.

        Progress is reported to ``app.jobs`` so clients can poll ``GET /jobs/{job_id}``.
        Re-runs are idempotent: existing transcript segments and subtitle artifacts are
        replaced.
        """
        video_path = Path(video_path)
        s = get_settings()

        job = self.session.get(AppJob, job_id)
        if job is None:
            raise ValueError(f"job {job_id} not found")

        asset = self.session.get(StudioMediaAsset, asset_id)
        if asset is None:
            raise ValueError(f"media asset {asset_id} not found")
        if not asset.title:
            asset.title = video_path.stem
            self.session.commit()

        if output_video_path is None:
            output_video_path = video_path.with_name(
                f"{video_path.stem}_subtitled{video_path.suffix}"
            )

        chunk_dir = s.cip_data_dir / "audio" / "chunks"

        try:
            _update_job(self.session, job, "processing", 0.02, "Limpiando artefactos anteriores…")
            _purge_existing_artifacts(self.session, asset_id)

            _update_job(self.session, job, "processing", 0.05, "Dividiendo audio en fragmentos…")
            chunks = split_audio_into_chunks(
                video_path,
                chunk_dir,
                chunk_seconds=chunk_minutes * 60,
                overlap_seconds=overlap_seconds,
                job_id=job_id,
            )
            n_chunks = len(chunks)
            logger.info("[%s] Audio split into %d chunk(s)", job_id, n_chunks)

            _update_job(self.session, job, "processing", 0.10, f"Transcribiendo {n_chunks} fragmento(s)…")

            transcriber = FasterWhisperTranscriber(model_size=model_size, language=language)
            all_asr_segments = []

            for chunk in chunks:
                chunk_asr, _ = transcriber.transcribe(chunk.path)
                for seg in chunk_asr:
                    global_start = seg.start + chunk.start_offset
                    global_end = seg.end + chunk.start_offset
                    # Drop the overlap zone: keep only segments whose content starts
                    # at or after the logical boundary of this chunk
                    if chunk.index > 0 and global_start < chunk.logical_start:
                        continue
                    all_asr_segments.append(
                        ASRSegment(start=global_start, end=global_end, text=seg.text)
                    )
                progress = 0.10 + 0.60 * ((chunk.index + 1) / n_chunks)
                _update_job(
                    self.session, job, "processing", round(progress, 2),
                    f"Fragmento {chunk.index + 1}/{n_chunks} transcrito"
                )

            logger.info("[%s] Transcription complete: %d segments total", job_id, len(all_asr_segments))

            _update_job(self.session, job, "processing", 0.75, "Generando archivo SRT…")
            srt_segments = [
                TranscriptSegment(start=asr.start, end=asr.end, text=asr.text)
                for asr in all_asr_segments
            ]
            srt_path = video_path.with_suffix(".srt")
            segments_to_srt(srt_segments, srt_path)

            _update_job(self.session, job, "processing", 0.80, "Quemando subtítulos en el vídeo…")
            final_video_path = embed_subtitles(video_path, srt_path, output_video_path)
            logger.info("[%s] Burned video saved to %s", job_id, final_video_path)

            _update_job(self.session, job, "processing", 0.90, "Guardando resultados en base de datos…")
            for seg in all_asr_segments:
                t = (seg.text or "").strip()
                if not t:
                    continue
                self.session.add(
                    StudioTranscriptSegment(
                        asset_id=asset_id,
                        start_time=seg.start,
                        end_time=seg.end,
                        text=t,
                        provenance="faster_whisper",
                        language=language,
                    )
                )
            self.session.add(
                StudioSubtitleArtifact(
                    asset_id=asset_id,
                    srt_path=str(srt_path),
                    burned_video_path=str(final_video_path),
                    language=language,
                )
            )
            self.session.commit()

            job.result_json = {
                "srt_path": str(srt_path),
                "burned_video_path": str(final_video_path),
            }
            _update_job(self.session, job, "completed", 1.0, "Pipeline de subtítulos completado")
            logger.info("[%s] Subtitle pipeline complete", job_id)

        except Exception as exc:
            logger.exception("[%s] Subtitle pipeline FAILED", job_id)
            _update_job(self.session, job, "failed", job.progress, error=str(exc))
            raise
        finally:
            # Clean up chunk WAV files
            chunk_job_dir = chunk_dir / str(job_id)
            if chunk_job_dir.exists():
                shutil.rmtree(chunk_job_dir, ignore_errors=True)

    def run_description_pipeline(
        self,
        asset_id: uuid.UUID,
        job_id: uuid.UUID,
        language: str = "es",
        provider: str = "local",
    ) -> None:
        """Generate an OpenAI SEO description from persisted transcript segments.

        Does not require the original video file — reads from ``studio.transcript_segments``.
        Re-runs are idempotent: the previous description for the asset is replaced.
        """
        job = self.session.get(AppJob, job_id)
        if job is None:
            raise ValueError(f"job {job_id} not found")

        asset = self.session.get(StudioMediaAsset, asset_id)
        if asset is None:
            raise ValueError(f"media asset {asset_id} not found")

        t0 = time.perf_counter()
        try:
            _update_job(self.session, job, "processing", 0.10, "Cargando segmentos de transcripción…")
            segments = (
                self.session.query(StudioTranscriptSegment)
                .filter(StudioTranscriptSegment.asset_id == asset_id)
                .order_by(StudioTranscriptSegment.start_time)
                .all()
            )
            if not segments:
                raise ValueError("No hay segmentos de transcripción para este asset. Ejecuta primero el pipeline de subtítulos.")

            logger.info("[%s] Loaded %d transcript segments (%d chars)", job_id, len(segments), sum(len(s.text) for s in segments))
            full_text = " ".join(seg.text for seg in segments)

            _update_job(self.session, job, "processing", 0.25, "Obteniendo keywords de tendencia…")
            trending = get_trending_keywords(self.session)

            _update_job(self.session, job, "processing", 0.30, "Generando descripción…")
            t_llm = time.perf_counter()
            if provider == "claude":
                body = generate_video_description(
                    full_text,
                    trending_keywords=trending,
                    title=asset.title or "",
                    language=language,
                )
                model_name = "claude"
            else:
                body = generate_video_description_local(
                    full_text,
                    trending_keywords=trending,
                    title=asset.title or "",
                    language=language,
                )
                model_name = get_settings().local_llm_model
            logger.info("[%s] Description generated via %s (%.1fs, %d chars)", job_id, provider, time.perf_counter() - t_llm, len(body))

            _update_job(self.session, job, "processing", 0.90, "Guardando descripción…")
            existing = self.session.execute(
                select(StudioGeneratedDescription).where(StudioGeneratedDescription.asset_id == asset_id)
            ).scalar_one_or_none()
            if existing is not None:
                existing.body = body
                existing.model_name = model_name
                existing.language = language
            else:
                self.session.add(
                    StudioGeneratedDescription(asset_id=asset_id, body=body, model_name=model_name, language=language)
                )
            self.session.commit()

            _update_job(self.session, job, "completed", 1.0, "Descripción generada")
            logger.info("[%s] Description pipeline COMPLETED — model=%s, total elapsed %.1fs", job_id, model_name, time.perf_counter() - t0)

        except Exception as exc:
            elapsed = time.perf_counter() - t0
            logger.exception("[%s] Description pipeline FAILED after %.1fs: %s", job_id, elapsed, exc)
            _update_job(self.session, job, "failed", job.progress, error=str(exc))
            raise
