from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from youtube_suite.infrastructure.persistence.base import Base


class StudioMediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = {"schema": "studio"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    market_video_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("market.videos.video_id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    transcript_segments: Mapped[list["StudioTranscriptSegment"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    descriptions: Mapped[list["StudioGeneratedDescription"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    subtitle_artifacts: Mapped[list["StudioSubtitleArtifact"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )


class StudioTranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    __table_args__ = {"schema": "studio"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studio.media_assets.id", ondelete="CASCADE"), index=True
    )
    start_time: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    end_time: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    provenance: Mapped[str] = mapped_column(String(64), default="faster_whisper")

    asset: Mapped[StudioMediaAsset] = relationship(back_populates="transcript_segments")


class StudioGeneratedDescription(Base):
    __tablename__ = "generated_descriptions"
    __table_args__ = {"schema": "studio"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studio.media_assets.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    asset: Mapped[StudioMediaAsset] = relationship(back_populates="descriptions")


class StudioSubtitleArtifact(Base):
    __tablename__ = "subtitle_artifacts"
    __table_args__ = {"schema": "studio"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studio.media_assets.id", ondelete="CASCADE"), index=True
    )
    srt_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    burned_video_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    asset: Mapped[StudioMediaAsset] = relationship(back_populates="subtitle_artifacts")
