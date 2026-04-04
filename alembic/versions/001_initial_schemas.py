"""initial market studio app schemas

Revision ID: 001
Revises:
Create Date: 2026-04-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS "market"')
    op.execute('CREATE SCHEMA IF NOT EXISTS "studio"')
    op.execute('CREATE SCHEMA IF NOT EXISTS "app"')

    op.create_table(
        "channels",
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subscriber_count", sa.BigInteger(), nullable=False),
        sa.Column("raw_snippet", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("inserted_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("channel_id"),
        schema="market",
    )

    op.create_table(
        "videos",
        sa.Column("video_id", sa.String(length=64), nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=1024), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration", sa.String(length=32), nullable=True),
        sa.Column("category_id", sa.String(length=32), nullable=True),
        sa.Column("raw_snippet", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("inserted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["channel_id"], ["market.channels.channel_id"]),
        sa.PrimaryKeyConstraint("video_id"),
        schema="market",
    )
    op.create_index(
        op.f("ix_market_videos_channel_id"), "videos", ["channel_id"], unique=False, schema="market"
    )

    op.create_table(
        "video_stats_timeseries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("video_id", sa.String(length=64), nullable=False),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("view_count", sa.BigInteger(), nullable=False),
        sa.Column("like_count", sa.BigInteger(), nullable=False),
        sa.Column("comment_count", sa.BigInteger(), nullable=False),
        sa.Column("favorite_count", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["market.videos.video_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="market",
    )
    op.create_index(
        op.f("ix_market_video_stats_timeseries_video_id"),
        "video_stats_timeseries",
        ["video_id"],
        unique=False,
        schema="market",
    )

    op.create_table(
        "comments",
        sa.Column("comment_id", sa.String(length=128), nullable=False),
        sa.Column("video_id", sa.String(length=64), nullable=False),
        sa.Column("author", sa.String(length=256), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("like_count", sa.BigInteger(), nullable=False),
        sa.Column("parent_id", sa.String(length=128), nullable=True),
        sa.Column("raw_snippet", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("inserted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["market.videos.video_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("comment_id"),
        schema="market",
    )
    op.create_index(
        op.f("ix_market_comments_video_id"), "comments", ["video_id"], unique=False, schema="market"
    )
    op.create_index(
        op.f("ix_market_comments_parent_id"), "comments", ["parent_id"], unique=False, schema="market"
    )

    op.create_table(
        "media_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("market_video_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["market_video_id"], ["market.videos.video_id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="studio",
    )
    op.create_index(
        op.f("ix_studio_media_assets_market_video_id"),
        "media_assets",
        ["market_video_id"],
        unique=False,
        schema="studio",
    )

    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_time", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("end_time", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("provenance", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["studio.media_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="studio",
    )
    op.create_index(
        op.f("ix_studio_transcript_segments_asset_id"),
        "transcript_segments",
        ["asset_id"],
        unique=False,
        schema="studio",
    )

    op.create_table(
        "generated_descriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["studio.media_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="studio",
    )
    op.create_index(
        op.f("ix_studio_generated_descriptions_asset_id"),
        "generated_descriptions",
        ["asset_id"],
        unique=False,
        schema="studio",
    )

    op.create_table(
        "subtitle_artifacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("srt_path", sa.String(length=1024), nullable=True),
        sa.Column("burned_video_path", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["studio.media_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="studio",
    )
    op.create_index(
        op.f("ix_studio_subtitle_artifacts_asset_id"),
        "subtitle_artifacts",
        ["asset_id"],
        unique=False,
        schema="studio",
    )

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("studio_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("market_video_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["market_video_id"], ["market.videos.video_id"]),
        sa.ForeignKeyConstraint(["studio_asset_id"], ["studio.media_assets.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="app",
    )
    op.create_index(op.f("ix_app_jobs_job_type"), "jobs", ["job_type"], unique=False, schema="app")
    op.create_index(op.f("ix_app_jobs_status"), "jobs", ["status"], unique=False, schema="app")
    op.create_index(
        op.f("ix_app_jobs_studio_asset_id"), "jobs", ["studio_asset_id"], unique=False, schema="app"
    )

    op.create_table(
        "job_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["app.jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="app",
    )
    op.create_index(
        op.f("ix_app_job_events_job_id"), "job_events", ["job_id"], unique=False, schema="app"
    )


def downgrade() -> None:
    op.drop_table("job_events", schema="app")
    op.drop_table("jobs", schema="app")
    op.drop_table("subtitle_artifacts", schema="studio")
    op.drop_table("generated_descriptions", schema="studio")
    op.drop_table("transcript_segments", schema="studio")
    op.drop_table("media_assets", schema="studio")
    op.drop_table("comments", schema="market")
    op.drop_table("video_stats_timeseries", schema="market")
    op.drop_table("videos", schema="market")
    op.drop_table("channels", schema="market")
