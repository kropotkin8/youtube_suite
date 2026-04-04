from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from youtube_suite.api.deps import get_db
from youtube_suite.api.schemas import (
    CommentsBody,
    MarketVideoOut,
    SearchSyncBody,
    TrendingSyncBody,
    VideoIdsBody,
)
from youtube_suite.application.market.ingestion_service import MarketIngestionService
from youtube_suite.infrastructure.persistence.market_models import MarketVideo

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


@router.get("/videos/{video_id}", response_model=MarketVideoOut)
def get_video(video_id: str, session: Session = Depends(get_db)) -> MarketVideo:
    """Retrieve a stored market video record by its YouTube video ID."""
    v = session.get(MarketVideo, video_id)
    if v is None:
        raise HTTPException(404, "video not found")
    return v
