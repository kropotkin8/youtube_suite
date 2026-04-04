from __future__ import annotations

from googleapiclient.discovery import build

from youtube_suite.config.settings import get_settings


def youtube_service():
    """Build and return an authenticated YouTube Data API v3 service client.

    Returns:
        A ``googleapiclient`` Resource object for the YouTube v3 API.

    Raises:
        ValueError: If ``YT_API_KEY`` is not configured in settings.
    """
    s = get_settings()
    if not s.yt_api_key:
        raise ValueError("YT_API_KEY not configured")
    return build("youtube", "v3", developerKey=s.yt_api_key)
