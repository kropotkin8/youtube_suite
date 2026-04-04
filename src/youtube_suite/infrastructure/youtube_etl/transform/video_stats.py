from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _int_or_zero(v: Any) -> int:
    """Convert a value to int, returning 0 on ``None``, ``TypeError``, or ``ValueError``.

    Args:
        v: Value to convert.

    Returns:
        Integer representation of ``v``, or ``0`` if conversion fails.
    """
    try:
        return int(v) if v is not None else 0
    except (TypeError, ValueError):
        return 0


def transform_video_stats(
    item: dict[str, Any],
    snapshot_time: datetime | None = None,
) -> dict[str, Any]:
    """Normalise a raw YouTube API statistics item into a flat dict for database insertion.

    Args:
        item: Raw video item dict containing a ``statistics`` sub-dict.
        snapshot_time: UTC timestamp for this snapshot. Defaults to ``datetime.now(UTC)``.

    Returns:
        Normalised dict with view/like/comment/favorite counts, or empty dict if no video ID.
    """
    vid = item.get("id")
    if not vid:
        return {}
    stats = item.get("statistics", {})
    return {
        "video_id": vid,
        "snapshot_time": snapshot_time or datetime.now(timezone.utc),
        "view_count": _int_or_zero(stats.get("viewCount")),
        "like_count": _int_or_zero(stats.get("likeCount")),
        "comment_count": _int_or_zero(stats.get("commentCount")),
        "favorite_count": _int_or_zero(stats.get("favoriteCount")),
    }


def transform_video_stats_batch(
    items: list[dict],
    snapshot_time: datetime | None = None,
) -> list[dict]:
    """Normalise a list of raw YouTube API statistics items, skipping items without an ID.

    Args:
        items: List of raw video item dicts containing ``statistics`` sub-dicts.
        snapshot_time: UTC timestamp applied to every row. Defaults to ``datetime.now(UTC)``.

    Returns:
        List of normalised stats dicts ready for database insertion.
    """
    return [transform_video_stats(i, snapshot_time) for i in items if i.get("id")]
