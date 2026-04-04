from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from youtube_suite.infrastructure.persistence.base import Base


class MarketChannel(Base):
    __tablename__ = "channels"
    __table_args__ = {"schema": "market"}

    channel_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subscriber_count: Mapped[int] = mapped_column(BigInteger, default=0)
    raw_snippet: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    videos: Mapped[list["MarketVideo"]] = relationship(back_populates="channel")


class MarketVideo(Base):
    __tablename__ = "videos"
    __table_args__ = {"schema": "market"}

    video_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    channel_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("market.channels.channel_id"), nullable=True, index=True
    )
    title: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(32), nullable=True)
    category_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_snippet: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    channel: Mapped[MarketChannel | None] = relationship(back_populates="videos")


class MarketVideoStats(Base):
    __tablename__ = "video_stats_timeseries"
    __table_args__ = {"schema": "market"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("market.videos.video_id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    view_count: Mapped[int] = mapped_column(BigInteger, default=0)
    like_count: Mapped[int] = mapped_column(BigInteger, default=0)
    comment_count: Mapped[int] = mapped_column(BigInteger, default=0)
    favorite_count: Mapped[int] = mapped_column(BigInteger, default=0)


class MarketComment(Base):
    __tablename__ = "comments"
    __table_args__ = {"schema": "market"}

    comment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    video_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("market.videos.video_id", ondelete="CASCADE"), nullable=False, index=True
    )
    author: Mapped[str | None] = mapped_column(String(256), nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    like_count: Mapped[int] = mapped_column(BigInteger, default=0)
    parent_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    raw_snippet: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    inserted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
