"""phase 5 director scenes and provider generations

Revision ID: 005_phase5
Revises: 004_hardening
Create Date: 2026-08-18
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005_phase5"
down_revision: Union[str, Sequence[str], None] = "004_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("videos", sa.Column("visual_mode", sa.String(length=20), nullable=False, server_default="stock"))
    op.add_column("videos", sa.Column("plan_json", sa.JSON(), nullable=True))

    op.create_table(
        "video_scenes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("video_id", sa.String(length=36), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.Column("narration", sa.Text(), nullable=False),
        sa.Column("visual_type", sa.String(length=20), nullable=False),
        sa.Column("visual_prompt", sa.Text(), nullable=False),
        sa.Column("visual_query", sa.String(length=200), nullable=False),
        sa.Column("caption", sa.String(length=400), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_job_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.String(length=36), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_video_scenes_video_id", "video_scenes", ["video_id"])
    op.create_index("ix_video_scenes_workspace_id", "video_scenes", ["workspace_id"])
    op.create_index("ix_video_scenes_provider_job_id", "video_scenes", ["provider_job_id"])
    op.create_index("ix_video_scenes_status", "video_scenes", ["status"])

    op.create_table(
        "video_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("video_id", sa.String(length=36), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("render_url", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("video_id", "version_number", name="uq_video_version"),
    )
    op.create_index("ix_video_versions_video_id", "video_versions", ["video_id"])

    op.create_table(
        "provider_generations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id", sa.String(length=36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("video_id", sa.String(length=36), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scene_id", sa.String(length=36), sa.ForeignKey("video_scenes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("duration", sa.Float(), nullable=False),
        sa.Column("provider_generation_id", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("credits_reserved", sa.Integer(), nullable=False),
        sa.Column("credits_captured", sa.Integer(), nullable=False),
        sa.Column("actual_cost", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("extra", sa.JSON(), nullable=True),
    )
    op.create_index("ix_provider_generations_workspace_id", "provider_generations", ["workspace_id"])
    op.create_index("ix_provider_generations_video_id", "provider_generations", ["video_id"])
    op.create_index("ix_provider_generations_provider_generation_id", "provider_generations", ["provider_generation_id"])
    op.create_index("ix_provider_generations_status", "provider_generations", ["status"])


def downgrade() -> None:
    op.drop_table("provider_generations")
    op.drop_table("video_versions")
    op.drop_table("video_scenes")
    op.drop_column("videos", "plan_json")
    op.drop_column("videos", "visual_mode")
