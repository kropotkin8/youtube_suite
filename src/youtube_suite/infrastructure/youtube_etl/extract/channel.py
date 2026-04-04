"""YouTube Data API v3 — channels.list."""
from __future__ import annotations

import logging
from typing import Optional

from googleapiclient.errors import HttpError

from youtube_suite.infrastructure.youtube_etl._client import youtube_service

logger = logging.getLogger(__name__)


def extract_channels(
    channel_ids: Optional[list[str]] = None,
    *,
    part: str = "snippet,statistics",
    max_results: int = 50,
) -> list[dict]:
    """Fetch raw channel items from the YouTube Data API by channel ID.

    Args:
        channel_ids: List of YouTube channel IDs to fetch (up to ``max_results``).
        part: Comma-separated API resource parts to include in the response.
        max_results: Maximum number of channels to request per API call.

    Returns:
        List of raw channel item dicts as returned by the YouTube API.
    """
    if not channel_ids:
        return []
    youtube = youtube_service()
    try:
        request = youtube.channels().list(
            part=part,
            id=",".join(channel_ids[:max_results]),
            maxResults=len(channel_ids[:max_results]),
        )
        response = request.execute()
        items = response.get("items", [])
        logger.info("channels.list: %d channels", len(items))
        return items
    except HttpError as e:
        logger.exception("channels.list error: %s", e)
        raise
