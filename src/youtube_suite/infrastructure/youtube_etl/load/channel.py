from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from youtube_suite.infrastructure.persistence.market_models import MarketChannel

logger = logging.getLogger(__name__)


def load_channels(session: Session, rows: Sequence[dict], *, upsert: bool = True) -> int:
    """Persist normalised channel rows to the ``market.channels`` table.

    Args:
        session: Active SQLAlchemy session.
        rows: Sequence of normalised channel dicts (must contain ``channel_id``).
        upsert: If ``True``, use PostgreSQL ``ON CONFLICT DO UPDATE``; otherwise uses ``merge``.

    Returns:
        Number of rows written.
    """
    rows = [r for r in rows if r.get("channel_id")]
    for r in rows:
        r.setdefault("inserted_at", datetime.now(timezone.utc))
    if not rows:
        return 0
    if upsert:
        stmt = pg_insert(MarketChannel).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[MarketChannel.channel_id],
            set_={
                MarketChannel.title: stmt.excluded.title,
                MarketChannel.description: stmt.excluded.description,
                MarketChannel.subscriber_count: stmt.excluded.subscriber_count,
                MarketChannel.raw_snippet: stmt.excluded.raw_snippet,
            },
        )
        session.execute(stmt)
    else:
        for r in rows:
            session.merge(MarketChannel(**r))
    session.commit()
    logger.info("load_channels: %d rows", len(rows))
    return len(rows)
