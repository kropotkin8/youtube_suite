from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import cast, func
from sqlalchemy import Date as SADate
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from youtube_suite.api.deps import get_db
from youtube_suite.api.schemas import (
    CategoryBreakdownItem,
    CategoryBreakdownResponse,
    CommentsBody,
    MarketOverviewResponse,
    MarketVideoListItem,
    MarketVideoListResponse,
    MarketVideoOut,
    SearchSyncBody,
    TopVideoItem,
    TopVideosResponse,
    TrendingSyncBody,
    VideoIdsBody,
    ViewsOverTimePoint,
    ViewsOverTimeResponse,
)
from youtube_suite.application.market.ingestion_service import MarketIngestionService
from youtube_suite.infrastructure.persistence.market_models import (
    MarketChannel,
    MarketComment,
    MarketVideo,
    MarketVideoStats,
)

router = APIRouter(prefix="/market", tags=["market"])


@router.post("/sync/trending")
def sync_trending(body: TrendingSyncBody, session: Session = Depends(get_db)) -> dict:
    """Fetch trending videos and sync full pipeline: channels, videos, stats, comments."""
    logger.info(f"[API] POST /market/sync/trending received: region={body.region}, limit={body.limit}, max_comment_pages={body.max_comment_pages}")
    svc = MarketIngestionService(session)
    result = svc.sync_trending_full(
        region=body.region,
        category_id=body.category_id,
        limit=body.limit,
        max_comment_pages=body.max_comment_pages,
    )
    logger.info(f"[API] POST /market/sync/trending completed: {result}")
    return result


@router.post("/sync/search")
def sync_search(body: SearchSyncBody, session: Session = Depends(get_db)) -> dict:
    """Search YouTube and sync full pipeline: channels, videos, stats, comments."""
    logger.info(f"[API] POST /market/sync/search received: query={body.query!r}, limit={body.limit}, region={body.region}, max_comment_pages={body.max_comment_pages}")
    svc = MarketIngestionService(session)
    result = svc.sync_search_full(
        query=body.query,
        limit=body.limit,
        region=body.region,
        max_comment_pages=body.max_comment_pages,
    )
    logger.info(f"[API] POST /market/sync/search completed: {result}")
    return result


@router.post("/sync/videos/by-ids")
def sync_videos_by_ids(body: VideoIdsBody, session: Session = Depends(get_db)) -> dict:
    """Fetch specific videos by ID from the YouTube API and upsert them into the database."""
    svc = MarketIngestionService(session)
    n = svc.sync_videos_by_ids(body.video_ids)
    return {"loaded": n}


@router.post("/sync/comments")
def sync_comments(body: CommentsBody, session: Session = Depends(get_db)) -> dict:
    """Fetch and load all comment threads for a given video into the database."""
    svc = MarketIngestionService(session)
    n = svc.sync_comments_for_video(body.video_id, max_pages=body.max_pages)
    return {"loaded": n}


@router.get("/overview", response_model=MarketOverviewResponse)
def market_overview(session: Session = Depends(get_db)) -> MarketOverviewResponse:
    """Aggregate KPIs: total videos, channels, comments, and sum of latest views."""
    total_videos = session.execute(select(func.count()).select_from(MarketVideo)).scalar_one()
    total_channels = session.execute(select(func.count()).select_from(MarketChannel)).scalar_one()
    total_comments = session.execute(select(func.count()).select_from(MarketComment)).scalar_one()

    latest_sq = (
        select(
            MarketVideoStats.video_id,
            func.max(MarketVideoStats.snapshot_time).label("max_snap"),
        )
        .group_by(MarketVideoStats.video_id)
        .subquery()
    )
    total_views = session.execute(
        select(func.coalesce(func.sum(MarketVideoStats.view_count), 0))
        .join(
            latest_sq,
            (MarketVideoStats.video_id == latest_sq.c.video_id)
            & (MarketVideoStats.snapshot_time == latest_sq.c.max_snap),
        )
    ).scalar_one()

    return MarketOverviewResponse(
        total_videos=total_videos,
        total_channels=total_channels,
        total_comments=total_comments,
        total_views=int(total_views),
    )


@router.get("/videos", response_model=MarketVideoListResponse)
def list_videos(
    page: int = 1,
    limit: int = 25,
    sort_by: str = "view_count",
    session: Session = Depends(get_db),
) -> MarketVideoListResponse:
    """Paginated list of market videos joined with their latest stats snapshot."""
    latest_sq = (
        select(
            MarketVideoStats.video_id,
            func.max(MarketVideoStats.snapshot_time).label("max_snap"),
        )
        .group_by(MarketVideoStats.video_id)
        .subquery()
    )
    stats_sq = (
        select(MarketVideoStats)
        .join(
            latest_sq,
            (MarketVideoStats.video_id == latest_sq.c.video_id)
            & (MarketVideoStats.snapshot_time == latest_sq.c.max_snap),
        )
        .subquery()
    )

    sort_col = {
        "view_count": stats_sq.c.view_count,
        "published_at": MarketVideo.published_at,
        "inserted_at": MarketVideo.inserted_at,
    }.get(sort_by, stats_sq.c.view_count)

    total = session.execute(
        select(func.count())
        .select_from(MarketVideo)
        .outerjoin(stats_sq, MarketVideo.video_id == stats_sq.c.video_id)
    ).scalar_one()

    rows = session.execute(
        select(
            MarketVideo.video_id,
            MarketVideo.title,
            MarketChannel.title.label("channel_title"),
            func.coalesce(stats_sq.c.view_count, 0).label("view_count"),
            func.coalesce(stats_sq.c.like_count, 0).label("like_count"),
            func.coalesce(stats_sq.c.comment_count, 0).label("comment_count"),
            MarketVideo.published_at,
            MarketVideo.duration,
            MarketVideo.category_id,
        )
        .outerjoin(stats_sq, MarketVideo.video_id == stats_sq.c.video_id)
        .outerjoin(MarketChannel, MarketVideo.channel_id == MarketChannel.channel_id)
        .order_by(sort_col.desc().nullslast())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return MarketVideoListResponse(
        total=total,
        page=page,
        limit=limit,
        videos=[
            MarketVideoListItem(
                video_id=r.video_id,
                title=r.title,
                channel_title=r.channel_title,
                view_count=r.view_count,
                like_count=r.like_count,
                comment_count=r.comment_count,
                published_at=r.published_at,
                duration=r.duration,
                category_id=r.category_id,
            )
            for r in rows
        ],
    )


@router.get("/charts/top-videos", response_model=TopVideosResponse)
def charts_top_videos(limit: int = 10, session: Session = Depends(get_db)) -> TopVideosResponse:
    """Top N videos by latest view_count snapshot."""
    latest_sq = (
        select(
            MarketVideoStats.video_id,
            func.max(MarketVideoStats.snapshot_time).label("max_snap"),
        )
        .group_by(MarketVideoStats.video_id)
        .subquery()
    )
    rows = session.execute(
        select(
            MarketVideo.video_id,
            MarketVideo.title,
            MarketVideoStats.view_count,
            MarketVideoStats.like_count,
            MarketVideoStats.comment_count,
        )
        .join(latest_sq, MarketVideo.video_id == latest_sq.c.video_id)
        .join(
            MarketVideoStats,
            (MarketVideoStats.video_id == latest_sq.c.video_id)
            & (MarketVideoStats.snapshot_time == latest_sq.c.max_snap),
        )
        .order_by(MarketVideoStats.view_count.desc())
        .limit(limit)
    ).all()

    return TopVideosResponse(
        videos=[
            TopVideoItem(
                video_id=r.video_id,
                title=r.title,
                view_count=r.view_count,
                like_count=r.like_count,
                comment_count=r.comment_count,
            )
            for r in rows
        ]
    )


@router.get("/charts/views-over-time", response_model=ViewsOverTimeResponse)
def charts_views_over_time(
    days: int = 30, session: Session = Depends(get_db)
) -> ViewsOverTimeResponse:
    """Daily aggregated views and likes for the last N days."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = session.execute(
        select(
            cast(MarketVideoStats.snapshot_time, SADate).label("date"),
            func.sum(MarketVideoStats.view_count).label("total_views"),
            func.sum(MarketVideoStats.like_count).label("total_likes"),
        )
        .where(MarketVideoStats.snapshot_time >= since)
        .group_by(cast(MarketVideoStats.snapshot_time, SADate))
        .order_by(cast(MarketVideoStats.snapshot_time, SADate))
    ).all()

    return ViewsOverTimeResponse(
        data=[
            ViewsOverTimePoint(
                date=str(r.date),
                total_views=int(r.total_views),
                total_likes=int(r.total_likes),
            )
            for r in rows
        ]
    )


@router.get("/charts/category-breakdown", response_model=CategoryBreakdownResponse)
def charts_category_breakdown(session: Session = Depends(get_db)) -> CategoryBreakdownResponse:
    """Count of videos and total views grouped by category_id."""
    latest_sq = (
        select(
            MarketVideoStats.video_id,
            func.max(MarketVideoStats.view_count).label("max_views"),
        )
        .group_by(MarketVideoStats.video_id)
        .subquery()
    )
    rows = session.execute(
        select(
            MarketVideo.category_id,
            func.count(MarketVideo.video_id).label("count"),
            func.coalesce(func.sum(latest_sq.c.max_views), 0).label("total_views"),
        )
        .outerjoin(latest_sq, MarketVideo.video_id == latest_sq.c.video_id)
        .group_by(MarketVideo.category_id)
        .order_by(func.count(MarketVideo.video_id).desc())
    ).all()

    return CategoryBreakdownResponse(
        data=[
            CategoryBreakdownItem(
                category_id=r.category_id,
                count=r.count,
                total_views=int(r.total_views),
            )
            for r in rows
        ]
    )


@router.get("/videos/{video_id}", response_model=MarketVideoOut)
def get_video(video_id: str, session: Session = Depends(get_db)) -> MarketVideo:
    """Retrieve a stored market video record by its YouTube video ID."""
    v = session.get(MarketVideo, video_id)
    if v is None:
        raise HTTPException(404, "video not found")
    return v
