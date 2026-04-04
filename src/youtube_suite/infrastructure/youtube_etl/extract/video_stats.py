"""YouTube Data API v3 — videos.list statistics."""
from __future__ import annotations

import logging

from googleapiclient.errors import HttpError

from youtube_suite.infrastructure.youtube_etl._client import youtube_service

logger = logging.getLogger(__name__)


def extract_video_stats(
    video_ids: list[str],
    *,
    part: str = "statistics",
    max_results: int = 50,
) -> list[dict]:
    """Fetch statistics-only video items from the YouTube Data API.

    Args:
        video_ids: List of YouTube video IDs to fetch statistics for (up to ``max_results``).
        part: Comma-separated API resource parts to include (typically ``"statistics"``).
        max_results: Maximum number of video IDs to include in a single API call.

    Returns:
        List of raw video item dicts containing the ``statistics`` field.
    """
    if not video_ids:
        return []
    youtube = youtube_service()
    chunk = video_ids[:max_results]
    try:
        request = youtube.videos().list(part=part, id=",".join(chunk), maxResults=len(chunk))
        response = request.execute()
        items = response.get("items", [])
        logger.info("videos.list(statistics): %d", len(items))
        return items
    except HttpError as e:
        logger.exception("videos.list(statistics) error: %s", e)
        raise
