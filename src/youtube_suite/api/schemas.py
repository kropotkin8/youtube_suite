from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobStatusEnum(str, Enum):
    uploaded = "uploaded"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class VideoIdsBody(BaseModel):
    video_ids: list[str] = Field(..., min_length=1)


class CommentsBody(BaseModel):
    video_id: str
    max_pages: int | None = None


class TrendingSyncBody(BaseModel):
    region: str = "ES"
    category_id: str | None = None
    limit: int = Field(50, ge=1, le=200)
    max_comment_pages: int | None = Field(3, ge=1, description="Max comment pages per video (~100 comments/page). None = all pages (slow).")


class SearchSyncBody(BaseModel):
    query: str
    limit: int = Field(25, ge=1, le=50)
    region: str | None = None
    max_comment_pages: int | None = Field(3, ge=1, description="Max comment pages per video (~100 comments/page). None = all pages (slow).")


class UploadResponse(BaseModel):
    asset_id: UUID
    filename: str
    message: str


class SubtitleRunRequest(BaseModel):
    model_size: str = "medium"
    language: str = "es"
    chunk_minutes: int = Field(10, ge=1, le=60)
    overlap_seconds: int = Field(5, ge=0, le=30)


class DescriptionRunRequest(BaseModel):
    pass


class SubtitleRunResponse(BaseModel):
    asset_id: UUID
    job_id: UUID
    message: str


class ShortsRunResponse(BaseModel):
    job_id: UUID
    message: str


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    progress: float
    message: str | None = None
    error: str | None = None


class ClipInfo(BaseModel):
    clip_id: str
    start: float
    end: float
    duration: float
    text: str
    speaker: str | None = None
    score: float
    path: str
    filename: str


class ClipsListResponse(BaseModel):
    job_id: UUID
    total_clips: int
    clips: list[ClipInfo]


class TrendingKeywordsResponse(BaseModel):
    keywords: list[str]


class MarketVideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    video_id: str
    channel_id: str | None
    title: str | None
    description: str | None
    published_at: datetime | None
    duration: str | None
    category_id: str | None
    inserted_at: datetime | None
