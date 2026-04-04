"""YouTube Data API v3 — commentThreads.list."""
from __future__ import annotations

import logging
from typing import Optional

from googleapiclient.errors import HttpError

from youtube_suite.infrastructure.youtube_etl._client import youtube_service

logger = logging.getLogger(__name__)


def extract_comments(
    video_id: str,
    *,
    part: str = "snippet,replies",
    max_results: int = 100,
    order: str = "time",
    page_token: Optional[str] = None,
) -> tuple[list[dict], Optional[str]]:
    """Fetch a single page of comment threads for a video from the YouTube Data API.

    Args:
        video_id: YouTube video ID to retrieve comments for.
        part: Comma-separated API resource parts to include.
        max_results: Maximum number of comment threads per page (capped at 100).
        order: Sort order — ``"time"`` or ``"relevance"``.
        page_token: Pagination token from a previous response, or ``None`` for the first page.

    Returns:
        Tuple of (list of raw comment thread dicts, next page token or ``None``).
    """
    youtube = youtube_service()
    try:
        request = youtube.commentThreads().list(
            part=part,
            videoId=video_id,
            maxResults=min(max_results, 100),
            order=order,
            textFormat="plainText",
            pageToken=page_token or "",
        )
        response = request.execute()
        items = response.get("items", [])
        next_token = response.get("nextPageToken")
        return items, next_token
    except HttpError as e:
        logger.exception("commentThreads.list error: %s", e)
        raise


def extract_all_comments_for_video(
    video_id: str,
    *,
    max_pages: Optional[int] = None,
    max_results_per_page: int = 100,
) -> list[dict]:
    """Fetch all comment threads and their replies for a video, paginating automatically.

    Top-level comments and inline reply comments are both included and normalised into a
    flat list of dicts with consistent keys.

    Args:
        video_id: YouTube video ID to retrieve comments for.
        max_pages: Maximum number of API pages to fetch. Defaults to all available pages.
        max_results_per_page: Number of comment threads to request per API call.

    Returns:
        Flat list of normalised comment dicts (top-level and replies combined).
    """
    all_comments: list[dict] = []
    page_token = None
    pages = 0
    while True:
        items, next_token = extract_comments(
            video_id, max_results=max_results_per_page, page_token=page_token
        )
        for thread in items:
            snippet = thread.get("snippet", {})
            top = snippet.get("topLevelComment", {})
            top_snippet = top.get("snippet", {})
            all_comments.append(
                {
                    "comment_id": top["id"],
                    "video_id": video_id,
                    "author": top_snippet.get("authorDisplayName"),
                    "text": top_snippet.get("textDisplay") or top_snippet.get("textOriginal"),
                    "published_at": top_snippet.get("publishedAt"),
                    "like_count": int(top_snippet.get("likeCount", 0)),
                    "parent_id": None,
                    "raw_snippet": top_snippet,
                }
            )
            reply_count = snippet.get("totalReplyCount", 0)
            if reply_count and "replies" in thread:
                for reply_comment in thread["replies"].get("comments", []):
                    rs = reply_comment.get("snippet", {})
                    all_comments.append(
                        {
                            "comment_id": reply_comment["id"],
                            "video_id": video_id,
                            "author": rs.get("authorDisplayName"),
                            "text": rs.get("textDisplay") or rs.get("textOriginal"),
                            "published_at": rs.get("publishedAt"),
                            "like_count": int(rs.get("likeCount", 0)),
                            "parent_id": rs.get("parentId"),
                            "raw_snippet": rs,
                        }
                    )
        pages += 1
        if not next_token or (max_pages and pages >= max_pages):
            break
        page_token = next_token
    return all_comments
