from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal
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
    beam_size: int = Field(5, ge=1, le=10)


class DescriptionRunRequest(BaseModel):
    language: str = Field("es", description="BCP-47 language code for the description (e.g. 'es', 'en', 'fr')")
    provider: Literal["claude", "local"] = Field(
        "local",
        description="LLM provider: 'local' (Ollama/Mistral) or 'claude' (Anthropic API)",
    )


class SubtitleRunResponse(BaseModel):
    asset_id: UUID
    job_id: UUID
    message: str


class ShortsRunRequest(BaseModel):
    language: str = "es"
    generate_vertical: bool = False
    generate_titles: bool = False


class ShortsRunResponse(BaseModel):
    job_id: UUID
    message: str


class RescoreRequest(BaseModel):
    weights: dict[str, float] = Field(
        default_factory=lambda: {"shortability": 0.5, "semantic": 0.2, "hook": 0.15, "speaker_change": 0.15}
    )


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: str
    progress: float
    message: str | None = None
    error: str | None = None


class ScoreBreakdown(BaseModel):
    semantic: float = 0.0
    audio_energy: float = 0.0
    speaker_change: float = 0.0
    hook_score: float = 0.0
    shortability: float = 0.0
    silence_ratio: float = 0.0


class ClipInfo(BaseModel):
    clip_id: str
    start: float
    end: float
    duration: float
    text: str
    speaker: str | None = None
    score: float
    score_breakdown: ScoreBreakdown | None = None
    hook_type: str | None = None
    title: str | None = None
    hashtags: list[str] = []
    path: str
    filename: str
    vertical_path: str | None = None
    vertical_filename: str | None = None


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
    has_chapters: bool


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
    # enriched
    tags: list[str] | None = None
    topic_categories: list[str] | None = None
    definition: str | None = None
    caption: bool | None = None
    thumbnail_url: str | None = None
    default_language: str | None = None
    made_for_kids: bool | None = None
    is_embeddable: bool | None = None
    license: str | None = None
    trending_date: date | None = None
    comments_disabled: bool | None = None
    ratings_disabled: bool | None = None
    engagement_rate: float | None = None


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
    # enriched
    thumbnail_url: str | None = None
    tags: list[str] | None = None
    definition: str | None = None
    default_language: str | None = None
    engagement_rate: float | None = None


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
    avg_engagement_rate: float | None = None


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


# ── ML Analysis schemas ───────────────────────────────────────────────────────

class ClusterPoint(BaseModel):
    video_id: str
    cluster: int
    engagement_rate: float
    duration_seconds: float
    category_id: str | None


class ClusterCentroid(BaseModel):
    cluster: int
    engagement_rate: float
    duration_seconds: float


class ClusteringResponse(BaseModel):
    points: list[ClusterPoint]
    centroids: list[ClusterCentroid]
    n_clusters: int


class EngagementPredictionPoint(BaseModel):
    category_id: str | None
    predicted: float
    actual: float


class EngagementPredictionResponse(BaseModel):
    points: list[EngagementPredictionPoint]
    r2: float
    coefficients: dict[str, float]


class AnomalyPoint(BaseModel):
    video_id: str
    title: str | None
    category_id: str | None
    engagement_rate: float
    anomaly_score: float


class AnomalyResponse(BaseModel):
    anomalies: list[AnomalyPoint]
    threshold: float


class TrendPoint(BaseModel):
    category_id: str | None
    slope: float
    direction: str  # "up" | "down" | "flat"
    r2: float


class TrendResponse(BaseModel):
    trends: list[TrendPoint]


# ── Studio extras ─────────────────────────────────────────────────────────────

class AssetShortsResponse(BaseModel):
    job_id: UUID
    total_clips: int
    clips: list[ClipInfo]


# ── Comment Intelligence ──────────────────────────────────────────────────────

class CommentIntelligenceRunResponse(BaseModel):
    asset_id: UUID
    job_id: UUID
    message: str


class SentimentDistribution(BaseModel):
    positive: float
    neutral: float
    negative: float


class TopicItem(BaseModel):
    label: str
    count: int
    percentage: float


class ClusterInfo(BaseModel):
    id: int
    label: str
    size: int
    top_comments: list[str]
    dominant_sentiment: str


class UnansweredQuestion(BaseModel):
    text: str
    likes: int


class CommentIntelligenceResult(BaseModel):
    video_id: str
    comment_count: int
    analyzed_at: datetime
    sentiment_distribution: SentimentDistribution
    toxicity_rate: float
    fan_vs_critic_ratio: float
    top_topics: list[TopicItem]
    clusters: list[ClusterInfo]
    unanswered_questions: list[UnansweredQuestion]
    summary_text: str


class CommentIntelligenceResponse(BaseModel):
    asset_id: UUID
    job_id: UUID | None = None
    result: CommentIntelligenceResult


# ── Smart Chapters ────────────────────────────────────────────────────────────

class ChapterInfo(BaseModel):
    start_seconds: float
    end_seconds: float
    title: str
    text: str


class SmartChaptersRunResponse(BaseModel):
    asset_id: UUID
    job_id: UUID
    message: str


class SmartChaptersResult(BaseModel):
    chapter_count: int
    generated_at: datetime
    youtube_format: str
    titling_method: str
    chapters: list[ChapterInfo]


class SmartChaptersResponse(BaseModel):
    asset_id: UUID
    job_id: UUID | None = None
    result: SmartChaptersResult
