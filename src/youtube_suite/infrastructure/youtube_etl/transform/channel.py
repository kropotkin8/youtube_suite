from __future__ import annotations

from typing import Any


def transform_channel(item: dict[str, Any]) -> dict[str, Any]:
    """Normalise a raw YouTube API channel item into a flat dict for database insertion.

    Args:
        item: Raw channel item dict from the YouTube Data API.

    Returns:
        Normalised dict with database-ready fields, or an empty dict if no channel ID is found.
    """
    sid = item.get("id") or item.get("snippet", {}).get("channelId")
    if not sid:
        return {}
    snippet = item.get("snippet", {})
    statistics = item.get("statistics", {})
    try:
        sub_count = int(statistics.get("subscriberCount", 0))
    except (TypeError, ValueError):
        sub_count = 0
    return {
        "channel_id": sid,
        "title": snippet.get("title"),
        "description": snippet.get("description"),
        "subscriber_count": sub_count,
        "raw_snippet": snippet,
    }


def transform_channels(items: list[dict]) -> list[dict]:
    """Normalise a list of raw YouTube API channel items.

    Args:
        items: List of raw channel item dicts from the YouTube Data API.

    Returns:
        List of normalised channel dicts (empty items are skipped).
    """
    return [transform_channel(i) for i in items if i]
