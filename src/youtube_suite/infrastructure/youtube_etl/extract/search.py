"""YouTube Data API v3 — search.list."""
from __future__ import annotations

import logging
from typing import Optional

from googleapiclient.errors import HttpError

from youtube_suite.infrastructure.youtube_etl._client import youtube_service

logger = logging.getLogger(__name__)


def extract_search(
    q: str,
    *,
    type: str = "video",
    max_results: int = 25,
    page_token: Optional[str] = None,
    region_code: Optional[str] = None,
) -> tuple[list[str], Optional[str]]:
    """Search the YouTube Data API and return a list of matching video IDs.

    Args:
        q: Search query string.
        type: Resource type to search for (e.g. ``"video"``).
        max_results: Maximum number of results to retrieve (capped at 50 by the API).
        page_token: Pagination token from a previous response, or ``None`` for the first page.
        region_code: Optional ISO 3166-1 alpha-2 region code to bias results.

    Returns:
        Tuple of (list of video ID strings, next page token or ``None``).
    """
    youtube = youtube_service()
    try:
        kwargs: dict = {
            "part": "id",
            "q": q,
            "type": type,
            "maxResults": min(max_results, 50),
        }
        if page_token:
            kwargs["pageToken"] = page_token
        if region_code:
            kwargs["regionCode"] = region_code
        response = youtube.search().list(**kwargs).execute()
        items = response.get("items", [])
        video_ids = []
        for it in items:
            vid = it.get("id", {}).get("videoId")
            if vid:
                video_ids.append(vid)
        return video_ids, response.get("nextPageToken")
    except HttpError as e:
        logger.exception("search.list error: %s", e)
        raise
