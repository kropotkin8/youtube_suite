from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from youtube_suite.infrastructure.persistence.market_models import MarketVideo

logger = logging.getLogger(__name__)


def load_videos(session: Session, rows: Sequence[dict], *, upsert: bool = True) -> int:
    """Persist normalised video rows to the ``market.videos`` table.

    Args:
        session: Active SQLAlchemy session.
        rows: Sequence of normalised video dicts (must contain ``video_id``).
        upsert: If ``True``, use PostgreSQL ``ON CONFLICT DO UPDATE``; otherwise plain insert.

    Returns:
        Number of rows written.
    """
    rows = [r for r in rows if r.get("video_id")]
    for r in rows:
        r.setdefault("inserted_at", datetime.now(timezone.utc))
    if not rows:
        return 0
    if upsert:
        stmt = pg_insert(MarketVideo).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[MarketVideo.video_id],
            set_={
                MarketVideo.channel_id: stmt.excluded.channel_id,
                MarketVideo.title: stmt.excluded.title,
                MarketVideo.description: stmt.excluded.description,
                MarketVideo.published_at: stmt.excluded.published_at,
                MarketVideo.duration: stmt.excluded.duration,
                MarketVideo.category_id: stmt.excluded.category_id,
                MarketVideo.raw_snippet: stmt.excluded.raw_snippet,
            },
        )
        session.execute(stmt)
    else:
        session.add_all([MarketVideo(**r) for r in rows])
    session.commit()
    logger.info("load_videos: %d rows", len(rows))
    return len(rows)
