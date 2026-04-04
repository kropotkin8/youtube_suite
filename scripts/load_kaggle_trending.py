"""Load Kaggle YouTube Trending Video Dataset into market tables.

Dataset: https://www.kaggle.com/datasets/datasnaek/youtube-new

Usage:
    python scripts/load_kaggle_trending.py [dataset_dir] [OPTIONS]

Options:
    --region US        Process only a specific region file (e.g. US, GB, ES)
    --skip-stats       Skip loading video_stats_timeseries
    --dry-run          Parse and print counts without writing to DB

Expected CSV columns (datasnaek/youtube-new):
    video_id, trending_date, title, channel_title, category_id,
    publish_time, tags, views, likes, dislikes, comment_count,
    thumbnail_link, comments_disabled, ratings_disabled, description
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

KAGGLE_DATASET = "datasnaek/youtube-new"


def _kaggle_env() -> dict[str, str]:
    """Build env vars for the Kaggle CLI from KAGGLE_API_TOKEN in .env.

    KAGGLE_API_TOKEN is expected to be the JSON content of kaggle.json,
    e.g.: {"username": "myuser", "key": "abc123..."}
    """
    env = os.environ.copy()

    env_file = Path(__file__).resolve().parents[1] / ".env"
    raw_token: str | None = None
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("KAGGLE_API_TOKEN="):
                raw_token = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

    if not raw_token:
        raw_token = os.environ.get("KAGGLE_API_TOKEN")

    if not raw_token:
        logger.warning("KAGGLE_API_TOKEN not found in .env — relying on existing Kaggle credentials")
        return env

    try:
        token = json.loads(raw_token)
        env["KAGGLE_USERNAME"] = token["username"]
        env["KAGGLE_KEY"] = token["key"]
    except (json.JSONDecodeError, KeyError):
        env["KAGGLE_KEY"] = raw_token
        username = env.get("KAGGLE_USERNAME")
        if not username and env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("KAGGLE_USERNAME="):
                    username = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        if username:
            env["KAGGLE_USERNAME"] = username
        else:
            logger.warning("KAGGLE_USERNAME not found — add it to .env alongside KAGGLE_API_TOKEN")

    return env


# Add the src directory to the path so the package can be imported directly
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from youtube_suite.infrastructure.persistence.session import get_engine, get_session_factory  # noqa: E402
from youtube_suite.infrastructure.youtube_etl.load.channel import load_channels  # noqa: E402
from youtube_suite.infrastructure.youtube_etl.load.video import load_videos  # noqa: E402
from youtube_suite.infrastructure.youtube_etl.load.video_stats import load_video_stats  # noqa: E402


def _stable_channel_id(channel_title: str) -> str:
    """Generate a stable synthetic channel_id from a channel title.

    Used when the dataset does not provide a real channelId.
    Prefix 'syn_' distinguishes synthetic IDs from real YouTube IDs.
    """
    digest = hashlib.md5(channel_title.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]
    return f"syn_{digest}"


def _parse_datetime(value: str) -> datetime | None:
    if not value or value.strip() == "":
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(value.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _parse_date_as_datetime(value: str) -> datetime | None:
    if not value or value.strip() == "":
        return None
    for fmt in ("%Y-%m-%d", "%y.%d.%m"):
        try:
            d = datetime.strptime(value.strip(), fmt)
            return d.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _process_csv(path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Read one region CSV and return (channels, videos, stats) as lists of dicts."""
    channels: dict[str, dict] = {}
    videos: dict[str, dict] = {}
    stats: list[dict] = []

    with path.open(encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            video_id = row.get("video_id", "").strip()
            if not video_id or video_id == "#NAME?":
                continue

            # datasnaek/youtube-new has channel_title but no channelId
            channel_title = row.get("channel_title", "").strip()
            if not channel_title:
                continue
            channel_id = _stable_channel_id(channel_title)

            # --- Channel ---
            if channel_id not in channels:
                channels[channel_id] = {
                    "channel_id": channel_id,
                    "title": channel_title,
                    "description": None,
                    "subscriber_count": 0,
                    "raw_snippet": None,
                }

            # --- Video (keep latest seen row per video_id) ---
            videos[video_id] = {
                "video_id": video_id,
                "channel_id": channel_id,
                "title": row.get("title", "").strip() or None,
                "description": row.get("description", "").strip() or None,
                "published_at": _parse_datetime(row.get("publish_time", "")),
                "duration": None,
                "category_id": str(row.get("category_id", "")).strip() or None,
                "raw_snippet": None,
            }

            # --- Stats ---
            snapshot_time = _parse_date_as_datetime(row.get("trending_date", ""))
            if snapshot_time is None:
                continue

            comments_disabled = row.get("comments_disabled", "False").strip().lower() == "true"
            stats.append({
                "video_id": video_id,
                "snapshot_time": snapshot_time,
                "view_count": _safe_int(row.get("views", "0")),
                "like_count": _safe_int(row.get("likes", "0")),
                "comment_count": 0 if comments_disabled else _safe_int(row.get("comment_count", "0")),
                "favorite_count": 0,
            })

    return list(channels.values()), list(videos.values()), stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Kaggle trending YouTube dataset into market tables.")
    parser.add_argument(
        "dataset_dir",
        type=Path,
        nargs="?",
        default=Path(__file__).resolve().parents[1] / "data" / "kaggle_trending",
        help="Directory containing region CSV files (default: <project>/data/kaggle_trending/)",
    )
    parser.add_argument("--region", metavar="CODE", help="Process only this region (e.g. US, GB)")
    parser.add_argument("--skip-stats", action="store_true", help="Skip loading video_stats_timeseries")
    parser.add_argument("--dry-run", action="store_true", help="Parse files without writing to DB")
    args = parser.parse_args()

    dataset_dir: Path = args.dataset_dir.resolve()
    downloaded = False
    needs_download = not dataset_dir.is_dir() or not any(dataset_dir.glob("*.csv"))
    if needs_download:
        dataset_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading %s into %s …", KAGGLE_DATASET, dataset_dir)
        kaggle_bin = shutil.which("kaggle")
        if not kaggle_bin:
            logger.error("kaggle CLI not found. Run: pip install kaggle")
            sys.exit(1)

        result = subprocess.run(
            [kaggle_bin, "datasets", "download", KAGGLE_DATASET, "-p", str(dataset_dir), "--unzip"],
            check=False,
            env=_kaggle_env(),
        )
        if result.returncode != 0:
            logger.error(
                "Kaggle download failed (exit %d). "
                "Check that KAGGLE_API_TOKEN and KAGGLE_USERNAME are set in .env.",
                result.returncode,
            )
            sys.exit(1)
        downloaded = True

    csv_files = sorted(dataset_dir.glob("*.csv"))
    if args.region:
        csv_files = [f for f in csv_files if f.stem.upper() == args.region.upper()]
    if not csv_files:
        logger.error("No CSV files found in %s (region filter: %s)", dataset_dir, args.region)
        sys.exit(1)

    if not args.dry_run:
        get_engine()
        session_factory = get_session_factory()

    total_channels = total_videos = total_stats = 0

    for csv_path in csv_files:
        logger.info("Processing %s …", csv_path.name)
        channels, videos, stats = _process_csv(csv_path)
        logger.info(
            "  Parsed: %d channels, %d videos, %d stat snapshots",
            len(channels), len(videos), len(stats),
        )

        if args.dry_run:
            total_channels += len(channels)
            total_videos += len(videos)
            total_stats += len(stats)
            continue

        with session_factory() as session:
            n_ch = load_channels(session, channels)
            n_vi = load_videos(session, videos)
            n_st = 0 if args.skip_stats else load_video_stats(session, stats)

        logger.info("  Loaded: %d channels, %d videos, %d stats", n_ch, n_vi, n_st)
        total_channels += n_ch
        total_videos += n_vi
        total_stats += n_st

    logger.info(
        "Done. Total: %d channels, %d videos, %d stat snapshots%s",
        total_channels, total_videos, total_stats,
        " [DRY RUN – nothing written]" if args.dry_run else "",
    )

    if downloaded and not args.dry_run:
        shutil.rmtree(dataset_dir)
        logger.info("Deleted downloaded dataset directory: %s", dataset_dir)


if __name__ == "__main__":
    main()
