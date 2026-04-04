"""YouTube Data API v3 — videos.list."""
from __future__ import annotations

import logging
from typing import Optional

from googleapiclient.errors import HttpError

from youtube_suite.infrastructure.youtube_etl._client import youtube_service

logger = logging.getLogger(__name__)


def extract_videos(
    video_ids: Optional[list[str]] = None,
    *,
    chart: Optional[str] = None,
    region_code: Optional[str] = None,
    video_category_id: Optional[str] = None,
    part: str = "snippet,contentDetails,statistics",
    max_results: int = 50,
) -> list[dict]:
    """Fetch raw video items from the YouTube Data API.

    Pass either ``video_ids`` for a direct lookup or ``chart="mostPopular"`` for trending videos.

    Args:
        video_ids: List of YouTube video IDs to fetch (up to 50).
        chart: Chart type — use ``"mostPopular"`` to retrieve trending videos.
        region_code: ISO 3166-1 alpha-2 region code (used with ``chart``).
        video_category_id: YouTube category ID to filter trending results.
        part: Comma-separated API resource parts to include in the response.
        max_results: Maximum number of items to request (capped at 50 by the API).

    Returns:
        List of raw video item dicts as returned by the YouTube API.
    """
    youtube = youtube_service()
    all_items: list[dict] = []
    try:
        if chart == "mostPopular":
            kwargs: dict = {
                "part": part,
                "chart": "mostPopular",
                "maxResults": min(max_results, 50),
            }
            if region_code:
                kwargs["regionCode"] = region_code
            if video_category_id:
                kwargs["videoCategoryId"] = video_category_id
            request = youtube.videos().list(**kwargs)
        elif video_ids:
            request = youtube.videos().list(
                part=part,
                id=",".join(video_ids[:50]),
                maxResults=min(len(video_ids), 50),
            )
        else:
            logger.warning("extract_videos: need video_ids or chart=mostPopular")
            return []
        response = request.execute()
        all_items = response.get("items", [])
        logger.info("videos.list: %d videos", len(all_items))
    except HttpError as e:
        logger.exception("videos.list error: %s", e)
        raise
    return all_items
