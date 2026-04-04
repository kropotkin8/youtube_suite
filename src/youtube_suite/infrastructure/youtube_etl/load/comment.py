from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from youtube_suite.infrastructure.persistence.market_models import MarketComment

logger = logging.getLogger(__name__)


# Max rows per batch: PostgreSQL limit is 65535 parameters per query.
# MarketComment has 9 columns → 65535 // 9 = 7281, using 1000 to be safe.
_BATCH_SIZE = 1000


def load_comments(session: Session, rows: Sequence[dict], *, upsert: bool = True) -> int:
    """Persist normalised comment rows to the ``market.comments`` table.

    Inserts in batches of 1000 rows to stay within PostgreSQL's 65535-parameter limit.

    Args:
        session: Active SQLAlchemy session.
        rows: Sequence of normalised comment dicts (must contain ``comment_id``).
        upsert: If ``True``, use PostgreSQL ``ON CONFLICT DO UPDATE``; otherwise uses ``merge``.

    Returns:
        Number of rows written.
    """
    # Deduplicate by comment_id — ON CONFLICT fails if the same PK appears twice in one batch
    seen: dict[str, dict] = {}
    for r in rows:
        if r.get("comment_id"):
            seen[r["comment_id"]] = r
    rows = list(seen.values())
    for r in rows:
        r.setdefault("inserted_at", datetime.now(timezone.utc))
    if not rows:
        return 0

    total = 0
    for i in range(0, len(rows), _BATCH_SIZE):
        batch = rows[i : i + _BATCH_SIZE]
        try:
            if upsert:
                stmt = pg_insert(MarketComment).values(batch)
                stmt = stmt.on_conflict_do_update(
                    index_elements=[MarketComment.comment_id],
                    set_={
                        MarketComment.video_id: stmt.excluded.video_id,
                        MarketComment.author: stmt.excluded.author,
                        MarketComment.text: stmt.excluded.text,
                        MarketComment.published_at: stmt.excluded.published_at,
                        MarketComment.like_count: stmt.excluded.like_count,
                        MarketComment.parent_id: stmt.excluded.parent_id,
                        MarketComment.raw_snippet: stmt.excluded.raw_snippet,
                    },
                )
                session.execute(stmt)
            else:
                for r in batch:
                    session.merge(MarketComment(**r))
            session.commit()
            total += len(batch)
            logger.info("load_comments: batch %d-%d inserted (%d total)", i, i + len(batch), total)
        except Exception:
            session.rollback()
            logger.exception("load_comments: failed on batch %d-%d, skipping", i, i + len(batch))

    return total
