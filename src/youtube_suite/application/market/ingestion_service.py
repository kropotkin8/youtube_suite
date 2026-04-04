from __future__ import annotations

import logging
from datetime import datetime, timezone

from googleapiclient.errors import HttpError
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from youtube_suite.infrastructure.youtube_etl.extract import (
    extract_all_comments_for_video,
    extract_channels,
    extract_search,
    extract_video_stats,
    extract_videos,
)
from youtube_suite.infrastructure.youtube_etl.load import (
    load_channels,
    load_comments,
    load_video_stats,
    load_videos,
)
from youtube_suite.infrastructure.youtube_etl.transform import (
    transform_channels,
    transform_comments,
    transform_video_stats_batch,
    transform_videos,
)
from youtube_suite.infrastructure.persistence.market_models import MarketVideo


class MarketIngestionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _sync_full_pipeline(
        self,
        video_rows: list[dict],
        max_comment_pages: int | None,
    ) -> dict:
        """Execute the full orchestrated pipeline: channels → videos → stats → comments.

        Args:
            video_rows: Already-transformed video dicts from extract + transform.
            max_comment_pages: Maximum comment pages per video. None = all.

        Returns:
            Summary dict with counts for each stage: channels_loaded, videos_loaded,
            stats_inserted, comments_loaded.
        """
        logger.info(f"[PIPELINE] Starting full sync pipeline for {len(video_rows)} videos")

        # 1. Extract and load channels (dedup from video rows)
        channel_ids = list({r["channel_id"] for r in video_rows if r["channel_id"]})
        logger.info(f"[PIPELINE] Step 1: Loading {len(channel_ids)} channels")
        raw_channels = extract_channels(channel_ids) if channel_ids else []
        channel_rows = transform_channels(raw_channels)
        ch_loaded = load_channels(self.session, channel_rows)
        logger.info(f"[PIPELINE] Step 1: ✓ Loaded {ch_loaded} channels")

        # 2. Load videos
        logger.info(f"[PIPELINE] Step 2: Loading {len(video_rows)} videos")
        vid_loaded = load_videos(self.session, video_rows)
        video_ids = [r["video_id"] for r in video_rows]
        logger.info(f"[PIPELINE] Step 2: ✓ Loaded {vid_loaded} videos")

        # 3. Snapshot stats
        logger.info(f"[PIPELINE] Step 3: Inserting stats snapshot for {len(video_ids)} videos")
        raw_stats = extract_video_stats(video_ids)
        snap_time = datetime.now(timezone.utc)
        stat_rows = transform_video_stats_batch(raw_stats, snapshot_time=snap_time)
        stats_inserted = load_video_stats(self.session, stat_rows)
        logger.info(f"[PIPELINE] Step 3: ✓ Inserted {stats_inserted} stats rows")

        # 4. Load comments for each video
        logger.info(f"[PIPELINE] Step 4: Fetching comments for {len(video_ids)} videos (max_pages={max_comment_pages})")
        all_comment_rows = []
        for i, vid_id in enumerate(video_ids, 1):
            logger.info(f"[PIPELINE] Step 4: Fetching comments for video {i}/{len(video_ids)}: {vid_id}")
            try:
                raw = extract_all_comments_for_video(vid_id, max_pages=max_comment_pages)
                all_comment_rows.extend(transform_comments(raw))
            except HttpError as e:
                logger.warning(f"[PIPELINE] Step 4: Skipping comments for {vid_id} — HTTP {e.status_code}: {e.reason}")
            except Exception as e:
                logger.exception(f"[PIPELINE] Step 4: Skipping comments for {vid_id} — unexpected error")
        comments_loaded = load_comments(self.session, all_comment_rows) if all_comment_rows else 0
        logger.info(f"[PIPELINE] Step 4: ✓ Loaded {comments_loaded} comments")

        logger.info(f"[PIPELINE] ✓ COMPLETE: channels={ch_loaded}, videos={vid_loaded}, stats={stats_inserted}, comments={comments_loaded}")

        return {
            "channels_loaded": ch_loaded,
            "videos_loaded": vid_loaded,
            "stats_inserted": stats_inserted,
            "comments_loaded": comments_loaded,
        }

    def sync_trending_full(
        self,
        region: str = "ES",
        category_id: str | None = None,
        limit: int = 50,
        max_comment_pages: int | None = None,
    ) -> dict:
        """Fetch trending videos and sync full pipeline: channels, videos, stats, comments.

        Args:
            region: ISO 3166-1 alpha-2 region code for trending charts.
            category_id: Optional YouTube video category ID to filter results.
            limit: Maximum number of videos to retrieve.
            max_comment_pages: Maximum comment pages per video. None = all.

        Returns:
            Summary dict with counts: channels_loaded, videos_loaded, stats_inserted,
            comments_loaded.
        """
        logger.info(f"[TRENDING] Fetching trending videos: region={region}, category_id={category_id}, limit={limit}")
        raw = extract_videos(
            chart="mostPopular",
            region_code=region or None,
            video_category_id=category_id,
            max_results=limit,
        )
        logger.info(f"[TRENDING] Extracted {len(raw)} raw video items from YouTube API")
        video_rows = transform_videos(raw)
        logger.info(f"[TRENDING] Transformed into {len(video_rows)} video rows")
        result = self._sync_full_pipeline(video_rows, max_comment_pages)
        logger.info(f"[TRENDING] ✓ DONE: {result}")
        return result

    def sync_search_full(
        self,
        query: str,
        limit: int = 25,
        region: str | None = None,
        max_comment_pages: int | None = None,
    ) -> dict:
        """Search YouTube and sync full pipeline: channels, videos, stats, comments.

        Args:
            query: Search query string.
            limit: Maximum number of results to retrieve.
            region: Optional ISO 3166-1 alpha-2 region code to filter results.
            max_comment_pages: Maximum comment pages per video. None = all.

        Returns:
            Summary dict with counts: channels_loaded, videos_loaded, stats_inserted,
            comments_loaded.
        """
        logger.info(f"[SEARCH] Searching YouTube: query={query!r}, limit={limit}, region={region}")
        video_ids, _ = extract_search(query, max_results=limit, region_code=region)
        logger.info(f"[SEARCH] Found {len(video_ids)} video IDs from search")
        if not video_ids:
            logger.warning(f"[SEARCH] No results found for query {query!r}")
            return {
                "channels_loaded": 0,
                "videos_loaded": 0,
                "stats_inserted": 0,
                "comments_loaded": 0,
            }
        logger.info(f"[SEARCH] Fetching full video details for {len(video_ids[:50])} videos (capped at 50)")
        raw = extract_videos(video_ids=video_ids[:50])
        logger.info(f"[SEARCH] Extracted {len(raw)} raw video items from YouTube API")
        video_rows = transform_videos(raw)
        logger.info(f"[SEARCH] Transformed into {len(video_rows)} video rows")
        result = self._sync_full_pipeline(video_rows, max_comment_pages)
        logger.info(f"[SEARCH] ✓ DONE: {result}")
        return result

    def sync_videos_by_ids(self, video_ids: list[str]) -> int:
        """Fetch specific videos by ID from the YouTube API and upsert them.

        Args:
            video_ids: List of YouTube video IDs to fetch.

        Returns:
            Number of video rows upserted.
        """
        raw = extract_videos(video_ids=video_ids)
        rows = transform_videos(raw)
        return load_videos(self.session, rows)

    def sync_comments_for_video(self, video_id: str, max_pages: int | None = None) -> int:
        """Fetch and upsert all comment threads for a given video.

        Args:
            video_id: YouTube video ID to fetch comments for.
            max_pages: Maximum number of API result pages to fetch. Defaults to all.

        Returns:
            Number of comment rows upserted.
        """
        raw = extract_all_comments_for_video(video_id, max_pages=max_pages)
        rows = transform_comments(raw)
        return load_comments(self.session, rows)
