from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from youtube_suite.api.deps import get_db
from youtube_suite.api.schemas import TrendingKeywordsResponse
from youtube_suite.application.insights.trending_service import get_trending_keywords

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/trending-keywords", response_model=TrendingKeywordsResponse)
def trending_keywords(days: int = 7, limit: int = 20, session: Session = Depends(get_db)) -> TrendingKeywordsResponse:
    """Return heuristic trending keywords extracted from recent high-view market videos."""
    kw = get_trending_keywords(session, days=days, limit=limit)
    return TrendingKeywordsResponse(keywords=kw)
