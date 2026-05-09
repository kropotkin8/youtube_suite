from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from youtube_suite.infrastructure.persistence.app_models import AppJob
from youtube_suite.infrastructure.persistence.studio_models import StudioTranscriptSegment

logger = logging.getLogger(__name__)


def create_chapters_job(session: Session, asset_id: uuid.UUID) -> uuid.UUID:
    job = AppJob(
        job_type="smart_chapters",
        status="pending",
        progress=0.0,
        studio_asset_id=asset_id,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job.id


def run_chapters_pipeline(
    session: Session,
    job_id: uuid.UUID,
    asset_id: uuid.UUID,
) -> None:
    job = session.get(AppJob, job_id)

    def _update(status: str, progress: float, message: str | None = None, err: str | None = None) -> None:
        job.status = status
        job.progress = progress
        job.message = message
        job.error = err
        job.updated_at = datetime.now(timezone.utc)
        session.commit()

    try:
        _update("processing", 0.05, "Cargando segmentos de transcripción…")

        rows = session.scalars(
            select(StudioTranscriptSegment)
            .where(StudioTranscriptSegment.asset_id == asset_id)
            .order_by(StudioTranscriptSegment.start_time)
        ).all()

        if not rows:
            raise ValueError(f"No transcript segments found for asset_id={asset_id}")

        segments = [
            {
                "start_time": float(r.start_time),
                "end_time": float(r.end_time),
                "text": r.text,
            }
            for r in rows
        ]

        def _cb(frac: float, msg: str) -> None:
            _update("processing", 0.05 + frac * 0.93, msg)

        from youtube_suite.infrastructure.nlp.chapters import generate_chapters
        result = generate_chapters(segments, progress_callback=_cb)

        job.result_json = result
        job.status = "completed"
        job.progress = 1.0
        job.message = f"Completado: {result['chapter_count']} capítulos generados"
        job.updated_at = datetime.now(timezone.utc)
        session.commit()

    except Exception as e:
        logger.exception("[%s] Smart chapters pipeline FAILED", job_id)
        _update("failed", job.progress, err=str(e))
