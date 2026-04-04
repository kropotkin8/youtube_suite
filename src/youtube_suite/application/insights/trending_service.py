from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from youtube_suite.infrastructure.persistence.market_models import MarketVideo, MarketVideoStats


def get_trending_keywords(session: Session, days: int = 7, limit: int = 20) -> list[str]:
    """Heuristic keywords from recent high-view market videos (replaces legacy mixed-schema query)."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    stmt = (
        select(MarketVideo.title)
        .join(MarketVideoStats, MarketVideoStats.video_id == MarketVideo.video_id)
        .where(MarketVideoStats.snapshot_time >= since)
        .order_by(MarketVideoStats.view_count.desc())
        .limit(limit)
    )
    titles = [row[0] for row in session.execute(stmt) if row[0]]

    keywords: list[str] = []
    for title in titles:
        for word in title.split():
            cleaned = word.strip(".,;:!¡?¿\"'()[]{}").lower()
            if len(cleaned) < 3:
                continue
            if cleaned not in keywords:
                keywords.append(cleaned)
    return keywords
