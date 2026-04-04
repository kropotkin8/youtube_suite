from __future__ import annotations

import logging
from typing import Sequence

from sqlalchemy.orm import Session

from youtube_suite.infrastructure.persistence.market_models import MarketVideoStats

logger = logging.getLogger(__name__)


def load_video_stats(session: Session, rows: Sequence[dict]) -> int:
    """Insert normalised video stats rows into the ``market.video_stats_timeseries`` table.

    Each call appends new snapshot rows; no deduplication is performed.

    Args:
        session: Active SQLAlchemy session.
        rows: Sequence of normalised stats dicts produced by the transform layer.

    Returns:
        Number of rows inserted.
    """
    if not rows:
        return 0
    for r in rows:
        session.add(MarketVideoStats(**r))
    session.commit()
    logger.info("load_video_stats: %d rows", len(rows))
    return len(rows)
