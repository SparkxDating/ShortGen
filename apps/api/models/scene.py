from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from apps.api.database.base import Base


class VideoScene(Base):
    __tablename__ = "video_scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    duration: Mapped[float] = mapped_column(Float, nullable=False, default=5)
    narration: Mapped[str] = mapped_column(Text, nullable=False, default="")
    visual_type: Mapped[str] = mapped_column(String(20), nullable=False, default="stock")
    visual_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    visual_query: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    caption: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    provider_job_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    asset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    video = relationship("Video", back_populates="scenes")


class VideoVersion(Base):
    __tablename__ = "video_versions"
    __table_args__ = (UniqueConstraint("video_id", "version_number", name="uq_video_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    render_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProviderGeneration(Base):
    __tablename__ = "provider_generations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    video_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scene_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("video_scenes.id", ondelete="SET NULL"), nullable=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    duration: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    provider_generation_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="QUEUED", index=True)
    credits_reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credits_captured: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_cost: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
