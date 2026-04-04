"""CLI: Market ETL (Typer)."""
from __future__ import annotations

import logging
from typing import Optional

import typer

from youtube_suite.infrastructure.persistence.session import get_session_factory
from youtube_suite.infrastructure.youtube_etl.extract import (
    extract_all_comments_for_video,
    extract_videos,
)
from youtube_suite.infrastructure.youtube_etl.load import (
    load_comments,
    load_videos,
)
from youtube_suite.infrastructure.youtube_etl.transform import (
    transform_comments,
    transform_videos,
)
from youtube_suite.application.market.ingestion_service import MarketIngestionService

cli = typer.Typer(name="cip", help="Creator Intel Platform CLI")


market_app = typer.Typer(help="YouTube market ETL")


@market_app.command("init-db")
def init_db_cmd() -> None:
    """Apply Alembic migrations (use: alembic upgrade head)."""
    typer.echo("Use: alembic upgrade head")


videos_app = typer.Typer(help="videos")


@videos_app.command("by-ids")
def videos_by_ids(video_ids: str = typer.Argument(...)) -> None:
    """Fetch and load specific videos by comma-separated YouTube video IDs.

    Args:
        video_ids: Comma-separated list of YouTube video IDs.
    """
    ids = [x.strip() for x in video_ids.split(",") if x.strip()]
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        raw = extract_videos(video_ids=ids)
        rows = transform_videos(raw)
        n = load_videos(session, rows)
    typer.echo(f"Loaded {n} videos.")




comments_app = typer.Typer(help="comments")


@comments_app.command("for-video")
def comments_for_video(
    video_id: str = typer.Argument(...),
    max_pages: Optional[int] = typer.Option(None, "--max-pages", "-n"),
) -> None:
    """Fetch and load all top-level comments and replies for a video.

    Args:
        video_id: YouTube video ID to fetch comments for.
        max_pages: Maximum number of API pages to retrieve. Defaults to all pages.
    """
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        raw = extract_all_comments_for_video(video_id, max_pages=max_pages)
        rows = transform_comments(raw)
        n = load_comments(session, rows)
    typer.echo(f"Loaded {n} comments.")


sync_app = typer.Typer(help="sync (orchestrated pipelines)")


@sync_app.command("trending")
def sync_trending(
    region: str = typer.Option("ES", "--region", "-r"),
    category_id: Optional[str] = typer.Option(None, "--category-id", "-c"),
    limit: int = typer.Option(50, "--limit", "-n"),
    max_comment_pages: Optional[int] = typer.Option(None, "--max-comment-pages", "-m"),
) -> None:
    """Fetch trending videos and sync full pipeline: channels, videos, stats, comments.

    Args:
        region: ISO 3166-1 alpha-2 region code for trending charts.
        category_id: Optional YouTube video category ID to filter results.
        limit: Maximum number of videos to retrieve.
        max_comment_pages: Maximum comment pages per video. None = all.
    """
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        svc = MarketIngestionService(session)
        result = svc.sync_trending_full(
            region=region,
            category_id=category_id,
            limit=limit,
            max_comment_pages=max_comment_pages,
        )
    typer.echo(
        f"Loaded {result['channels_loaded']} channels, "
        f"{result['videos_loaded']} videos, "
        f"{result['stats_inserted']} stats, "
        f"{result['comments_loaded']} comments."
    )


@sync_app.command("search")
def sync_search(
    query: str = typer.Argument(...),
    limit: int = typer.Option(25, "--limit", "-n"),
    region: Optional[str] = typer.Option(None, "--region", "-r"),
    max_comment_pages: Optional[int] = typer.Option(None, "--max-comment-pages", "-m"),
) -> None:
    """Search YouTube and sync full pipeline: channels, videos, stats, comments.

    Args:
        query: Search query string.
        limit: Maximum number of results to retrieve.
        region: Optional ISO 3166-1 alpha-2 region code to filter results.
        max_comment_pages: Maximum comment pages per video. None = all.
    """
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        svc = MarketIngestionService(session)
        result = svc.sync_search_full(
            query=query,
            limit=limit,
            region=region,
            max_comment_pages=max_comment_pages,
        )
    typer.echo(
        f"Loaded {result['channels_loaded']} channels, "
        f"{result['videos_loaded']} videos, "
        f"{result['stats_inserted']} stats, "
        f"{result['comments_loaded']} comments."
    )


market_app.add_typer(videos_app, name="videos")
market_app.add_typer(comments_app, name="comments")
market_app.add_typer(sync_app, name="sync")

cli.add_typer(market_app, name="market")


def main() -> None:
    """Configure logging and launch the Typer CLI application."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    cli()


if __name__ == "__main__":
    main()
