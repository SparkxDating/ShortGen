"""production hardening

Revision ID: 004_hardening
Revises: 003_phase3
Create Date: 2026-08-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_hardening"
down_revision: Union[str, Sequence[str], None] = "003_phase3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("worker_id", sa.String(length=80), nullable=True))
    op.add_column("jobs", sa.Column("attempt_started_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "job_outbox",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_job_outbox_job_id", "job_outbox", ["job_id"], unique=True)
    op.create_index("ix_job_outbox_status", "job_outbox", ["status"])

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("video_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "workspace_id", "key", name="uq_idempotency"),
    )
    op.create_index("ix_idempotency_keys_user_id", "idempotency_keys", ["user_id"])
    op.create_index("ix_idempotency_keys_workspace_id", "idempotency_keys", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_table("job_outbox")
    op.drop_column("jobs", "attempt_started_at")
    op.drop_column("jobs", "worker_id")
    op.drop_column("jobs", "heartbeat_at")
