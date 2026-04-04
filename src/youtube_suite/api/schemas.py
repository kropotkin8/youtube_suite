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
    language: str = Field("es", description="BCP-47 language code for the description (e.g. 'es', 'en', 'fr')")


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


class AssetListItem(BaseModel):
    id: UUID
    filename: str
    title: str | None
    duration_seconds: float | None
    market_video_id: str | None
    created_at: datetime
    has_transcript: bool
    has_description: bool
    has_shorts: bool


class AssetListResponse(BaseModel):
    total: int
    assets: list[AssetListItem]


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


# ── Market listing & charts ───────────────────────────────────────────────────

class MarketVideoListItem(BaseModel):
    video_id: str
    title: str | None
    channel_title: str | None
    view_count: int
    like_count: int
    comment_count: int
    published_at: datetime | None
    duration: str | None
    category_id: str | None


class MarketVideoListResponse(BaseModel):
    total: int
    page: int
    limit: int
    videos: list[MarketVideoListItem]


class MarketOverviewResponse(BaseModel):
    total_videos: int
    total_channels: int
    total_comments: int
    total_views: int


class TopVideoItem(BaseModel):
    video_id: str
    title: str | None
    view_count: int
    like_count: int
    comment_count: int


class TopVideosResponse(BaseModel):
    videos: list[TopVideoItem]


class ViewsOverTimePoint(BaseModel):
    date: str
    total_views: int
    total_likes: int


class ViewsOverTimeResponse(BaseModel):
    data: list[ViewsOverTimePoint]


class CategoryBreakdownItem(BaseModel):
    category_id: str | None
    count: int
    total_views: int


class CategoryBreakdownResponse(BaseModel):
    data: list[CategoryBreakdownItem]


# ── Studio extras ─────────────────────────────────────────────────────────────

class AssetShortsResponse(BaseModel):
    job_id: UUID
    total_clips: int
    clips: list[ClipInfo]
