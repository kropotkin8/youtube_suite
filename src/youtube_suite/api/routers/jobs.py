from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from youtube_suite.api.deps import get_db
from youtube_suite.api.schemas import ClipInfo, ClipsListResponse, JobStatusResponse
from youtube_suite.infrastructure.persistence.app_models import AppJob

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: uuid.UUID, session: Session = Depends(get_db)) -> JobStatusResponse:
    """Return the current status, progress, and messages for a background job."""
    j = session.get(AppJob, job_id)
    if j is None:
        raise HTTPException(404, "job not found")
    return JobStatusResponse(
        job_id=j.id,
        status=j.status,
        progress=j.progress,
        message=j.message,
        error=j.error,
    )


@router.get("/{job_id}/clips", response_model=ClipsListResponse)
def job_clips(job_id: uuid.UUID, session: Session = Depends(get_db)) -> ClipsListResponse:
    """Return the list of generated clip metadata for a completed shorts job."""
    j = session.get(AppJob, job_id)
    if j is None:
        raise HTTPException(404, "job not found")
    if j.status != "completed" or not j.result_json:
        raise HTTPException(400, "job not completed")
    clips_raw = j.result_json.get("clips", [])
    clips = [ClipInfo(**c) for c in clips_raw]
    return ClipsListResponse(job_id=job_id, total_clips=len(clips), clips=clips)


@router.get("/{job_id}/clips/{clip_id}")
def download_clip(job_id: uuid.UUID, clip_id: str, session: Session = Depends(get_db)):
    """Stream a specific clip video file from a completed shorts job as an MP4 download."""
    j = session.get(AppJob, job_id)
    if j is None or not j.result_json:
        raise HTTPException(404, "job not found")
    clips = j.result_json.get("clips", [])
    clip = next((c for c in clips if c.get("clip_id") == clip_id), None)
    if not clip:
        raise HTTPException(404, "clip not found")
    p = Path(clip["path"])
    if not p.exists():
        raise HTTPException(404, "file missing")
    return FileResponse(path=str(p), filename=clip["filename"], media_type="video/mp4")
