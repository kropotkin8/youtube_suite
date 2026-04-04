from __future__ import annotations

from datetime import datetime
from typing import Any

from dateutil import parser as date_parser


def _parse_datetime(s: str | None) -> datetime | None:
    """Parse an ISO 8601 datetime string, returning ``None`` on failure or empty input.

    Args:
        s: ISO 8601 datetime string or ``None``.

    Returns:
        Parsed ``datetime`` object, or ``None`` if the input is blank or unparseable.
    """
    if not s:
        return None
    try:
        return date_parser.isoparse(s)
    except Exception:
        return None


def transform_video(item: dict[str, Any]) -> dict[str, Any]:
    """Normalise a raw YouTube API video item into a flat dict for database insertion.

    Args:
        item: Raw video item dict from the YouTube Data API.

    Returns:
        Normalised dict with database-ready fields, or an empty dict if the item has no ID.
    """
    vid = item.get("id")
    if not vid:
        return {}
    snippet = item.get("snippet", {})
    content = item.get("contentDetails", {})
    return {
        "video_id": vid,
        "channel_id": snippet.get("channelId"),
        "title": snippet.get("title"),
        "description": snippet.get("description"),
        "published_at": _parse_datetime(snippet.get("publishedAt")),
        "duration": content.get("duration"),
        "category_id": snippet.get("categoryId"),
        "raw_snippet": snippet,
    }


def transform_videos(items: list[dict]) -> list[dict]:
    """Normalise a list of raw YouTube API video items.

    Args:
        items: List of raw video item dicts from the YouTube Data API.

    Returns:
        List of normalised video dicts (empty items are skipped).
    """
    return [transform_video(i) for i in items if i]
