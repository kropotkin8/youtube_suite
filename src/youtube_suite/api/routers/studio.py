from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session


from youtube_suite.api.deps import get_db
from youtube_suite.api.schemas import (
    AssetListItem,
    AssetListResponse,
    AssetShortsResponse,
    ClipInfo,
    DescriptionRunRequest,
    ShortsRunResponse,
    SubtitleRunRequest,
    SubtitleRunResponse,
    UploadResponse,
)
from youtube_suite.application.shorts.shorts_service import (
    create_shorts_job,
    run_shorts_pipeline,
)
from youtube_suite.application.studio.subtitle_service import (
    StudioSubtitleService,
    create_description_job,
    create_subtitle_job,
)
from youtube_suite.infrastructure.persistence.app_models import AppJob
from youtube_suite.infrastructure.persistence.studio_models import (
    StudioGeneratedDescription,
    StudioMediaAsset,
    StudioSubtitleArtifact,
    StudioTranscriptSegment,
)
from youtube_suite.infrastructure.storage.local_storage import LocalFileStorage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/studio", tags=["studio"])


@router.post("/assets/upload", response_model=UploadResponse)
async def upload_asset(
    file: UploadFile = File(...), session: Session = Depends(get_db)
) -> UploadResponse:
    """Accept a video file upload, persist it to local storage, and create a media asset record."""
    data = await file.read()
    storage = LocalFileStorage()
    key, path = storage.save_upload(file.filename or "video.bin", data)
    asset = StudioMediaAsset(
        storage_key=key,
        filename=file.filename or key,
        title=Path(file.filename or "").stem,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return UploadResponse(asset_id=asset.id, filename=asset.filename, message="ok")


@router.get("/assets", response_model=AssetListResponse)
def list_assets(session: Session = Depends(get_db)) -> AssetListResponse:
    """List all media assets with flags indicating available transcription, description and shorts."""
    assets = session.scalars(
        select(StudioMediaAsset).order_by(StudioMediaAsset.created_at.desc())
    ).all()

    items = []
    for a in assets:
        has_transcript = (
            session.execute(
                select(StudioTranscriptSegment.id)
                .where(StudioTranscriptSegment.asset_id == a.id)
                .limit(1)
            ).scalar_one_or_none()
            is not None
        )
        has_description = (
            session.execute(
                select(StudioGeneratedDescription.id)
                .where(StudioGeneratedDescription.asset_id == a.id)
                .limit(1)
            ).scalar_one_or_none()
            is not None
        )
        has_shorts = (
            session.execute(
                select(AppJob.id)
                .where(AppJob.studio_asset_id == a.id, AppJob.job_type == "shorts", AppJob.status == "completed")
                .limit(1)
            ).scalar_one_or_none()
            is not None
        )
        items.append(
            AssetListItem(
                id=a.id,
                filename=a.filename,
                title=a.title,
                duration_seconds=float(a.duration_seconds) if a.duration_seconds is not None else None,
                market_video_id=a.market_video_id,
                created_at=a.created_at,
                has_transcript=has_transcript,
                has_description=has_description,
                has_shorts=has_shorts,
            )
        )

    return AssetListResponse(total=len(items), assets=items)


@router.post("/assets/{asset_id}/subtitles/run", response_model=SubtitleRunResponse)
def run_subtitles(
    asset_id: uuid.UUID,
    body: SubtitleRunRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
) -> SubtitleRunResponse:
    """Enqueue the subtitle pipeline for a media asset as a background task."""
    asset = session.get(StudioMediaAsset, asset_id)
    if asset is None:
        raise HTTPException(404, "asset not found")
    storage = LocalFileStorage()
    video_path = storage.path_for_key(asset.storage_key)
    if not video_path.exists():
        raise HTTPException(400, "file missing on disk")

    jid = create_subtitle_job(session, asset_id, video_path, body.model_dump())

    def _job() -> None:
        from youtube_suite.infrastructure.persistence.session import get_session_factory

        logger.info("[%s] Subtitle pipeline started (model=%s)", jid, body.model_size)
        SessionLocal = get_session_factory()
        try:
            with SessionLocal() as sess:
                svc = StudioSubtitleService(sess)
                svc.run_subtitle_pipeline_chunked(
                    video_path,
                    asset_id=asset_id,
                    job_id=jid,
                    model_size=body.model_size,
                    language=body.language,
                    chunk_minutes=body.chunk_minutes,
                    overlap_seconds=body.overlap_seconds,
                )
        except Exception:
            logger.exception("[%s] Subtitle pipeline FAILED", jid)

    background_tasks.add_task(_job)
    return SubtitleRunResponse(asset_id=asset_id, job_id=jid, message="subtitle pipeline started")


@router.post("/assets/{asset_id}/description/run", response_model=SubtitleRunResponse)
def run_description(
    asset_id: uuid.UUID,
    body: DescriptionRunRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
) -> SubtitleRunResponse:
    """Enqueue description generation from existing transcript segments."""
    asset = session.get(StudioMediaAsset, asset_id)
    if asset is None:
        raise HTTPException(404, "asset not found")

    jid = create_description_job(session, asset_id)
    _language = body.language

    def _job() -> None:
        from youtube_suite.infrastructure.persistence.session import get_session_factory

        logger.info("[%s] Description pipeline started for asset %s", jid, asset_id)
        SessionLocal = get_session_factory()
        try:
            with SessionLocal() as sess:
                svc = StudioSubtitleService(sess)
                svc.run_description_pipeline(asset_id=asset_id, job_id=jid, language=_language)
        except Exception:
            logger.exception("[%s] Description pipeline FAILED", jid)

    background_tasks.add_task(_job)
    return SubtitleRunResponse(asset_id=asset_id, job_id=jid, message="description pipeline started")


@router.post("/assets/{asset_id}/shorts/run", response_model=ShortsRunResponse)
def run_shorts(
    asset_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
) -> ShortsRunResponse:
    """Create a shorts job record and enqueue the shorts pipeline as a background task."""
    asset = session.get(StudioMediaAsset, asset_id)
    if asset is None:
        raise HTTPException(404, "asset not found")
    storage = LocalFileStorage()
    video_path = storage.path_for_key(asset.storage_key)
    if not video_path.exists():
        raise HTTPException(400, "file missing")
    jid = create_shorts_job(session, asset_id, video_path)

    def _work() -> None:
        from youtube_suite.infrastructure.persistence.session import get_session_factory

        logger.info("[%s] Shorts pipeline started for asset %s", jid, asset_id)
        SessionLocal = get_session_factory()
        try:
            with SessionLocal() as sess:
                run_shorts_pipeline(sess, jid, video_path)
            logger.info("[%s] Shorts pipeline complete", jid)
        except Exception:
            logger.exception("[%s] Shorts pipeline FAILED", jid)
            raise

    background_tasks.add_task(_work)
    return ShortsRunResponse(job_id=jid, message="shorts pipeline started")


@router.get("/assets/{asset_id}")
def get_asset(asset_id: uuid.UUID, session: Session = Depends(get_db)) -> dict:
    """Retrieve metadata for a studio media asset by its ID."""
    a = session.get(StudioMediaAsset, asset_id)
    if a is None:
        raise HTTPException(404, "not found")
    return {
        "id": str(a.id),
        "filename": a.filename,
        "title": a.title,
        "market_video_id": a.market_video_id,
        "storage_key": a.storage_key,
    }


@router.get("/assets/{asset_id}/transcript")
def get_transcript(asset_id: uuid.UUID, session: Session = Depends(get_db)) -> dict:
    """Return all transcript segments for a media asset, ordered by storage insertion."""
    rows = session.scalars(
        select(StudioTranscriptSegment).where(
            StudioTranscriptSegment.asset_id == asset_id
        )
    ).all()
    return {
        "segments": [
            {"start": float(r.start_time), "end": float(r.end_time), "text": r.text}
            for r in rows
        ]
    }


@router.get("/assets/{asset_id}/description")
def get_description(asset_id: uuid.UUID, session: Session = Depends(get_db)) -> dict:
    """Return the most recently generated YouTube description for a media asset."""
    row = session.execute(
        select(StudioGeneratedDescription)
        .where(StudioGeneratedDescription.asset_id == asset_id)
        .order_by(StudioGeneratedDescription.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "no description")
    return {"body": row.body, "model": row.model_name}


@router.get("/assets/{asset_id}/video")
def stream_video(asset_id: uuid.UUID, session: Session = Depends(get_db)) -> FileResponse:
    """Stream the original uploaded video file."""
    a = session.get(StudioMediaAsset, asset_id)
    if a is None:
        raise HTTPException(404, "asset not found")
    storage = LocalFileStorage()
    p = storage.path_for_key(a.storage_key)
    if not p.exists():
        raise HTTPException(404, "file missing on disk")
    return FileResponse(
        path=str(p),
        media_type="video/mp4",
        filename=a.filename,
        headers={"Accept-Ranges": "bytes"},
    )


@router.get("/assets/{asset_id}/video/subtitled")
def stream_subtitled_video(asset_id: uuid.UUID, session: Session = Depends(get_db)) -> FileResponse:
    """Stream the burned-subtitle version of the video if it exists."""
    a = session.get(StudioMediaAsset, asset_id)
    if a is None:
        raise HTTPException(404, "asset not found")

    artifact = session.execute(
        select(StudioSubtitleArtifact)
        .where(StudioSubtitleArtifact.asset_id == asset_id)
        .where(StudioSubtitleArtifact.burned_video_path.isnot(None))
        .order_by(desc(StudioSubtitleArtifact.created_at))
        .limit(1)
    ).scalar_one_or_none()

    if artifact is None:
        raise HTTPException(404, "no subtitled video available")

    p = Path(artifact.burned_video_path)
    if not p.exists():
        raise HTTPException(404, "subtitled file missing on disk")

    return FileResponse(
        path=str(p),
        media_type="video/mp4",
        filename=f"{a.title or a.filename}_subtitled.mp4",
        headers={"Accept-Ranges": "bytes"},
    )


@router.get("/assets/{asset_id}/shorts", response_model=AssetShortsResponse)
def get_asset_shorts(asset_id: uuid.UUID, session: Session = Depends(get_db)) -> AssetShortsResponse:
    """Return clips from the most recent completed shorts job for this asset."""
    a = session.get(StudioMediaAsset, asset_id)
    if a is None:
        raise HTTPException(404, "asset not found")

    job = session.execute(
        select(AppJob)
        .where(AppJob.studio_asset_id == asset_id)
        .where(AppJob.job_type == "shorts")
        .where(AppJob.status == "completed")
        .order_by(desc(AppJob.created_at))
        .limit(1)
    ).scalar_one_or_none()

    if job is None:
        raise HTTPException(404, "no completed shorts job for this asset")
    if not job.result_json:
        raise HTTPException(400, "shorts job has no result data")

    clips = [ClipInfo(**c) for c in job.result_json.get("clips", [])]
    return AssetShortsResponse(job_id=job.id, total_clips=len(clips), clips=clips)
