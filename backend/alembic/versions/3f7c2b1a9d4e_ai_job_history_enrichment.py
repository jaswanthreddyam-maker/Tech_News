"""ai job history enrichment

Revision ID: 3f7c2b1a9d4e
Revises: 6f679dff3088
Create Date: 2026-06-10 16:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # revision identifiers, used by Alembic.

revision: str = "3f7c2b1a9d4e"
down_revision: str | Sequence[str] | None = "6f679dff3088"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "ai_job_history",
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="disabled"),
    )
    op.add_column("ai_job_history", sa.Column("task_type", sa.String(length=50), nullable=True))
    op.add_column("ai_job_history", sa.Column("prompt_version", sa.String(length=50), nullable=True))
    op.add_column(
        "ai_job_history",
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "ai_job_history",
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0"),
    )
    op.add_column(
        "ai_job_history",
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "ai_job_history",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("ai_job_history", sa.Column("error", sa.Text(), nullable=True))
    op.add_column("ai_job_history", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_job_history", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        """
        UPDATE ai_job_history
        SET
            total_tokens = COALESCE(prompt_tokens, 0) + COALESCE(completion_tokens, 0),
            cost_usd = COALESCE(cost, 0)
        """
    )

    op.create_index(op.f("ix_ai_job_history_provider"), "ai_job_history", ["provider"], unique=False)
    op.create_index(op.f("ix_ai_job_history_task_type"), "ai_job_history", ["task_type"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_ai_job_history_task_type"), table_name="ai_job_history")
    op.drop_index(op.f("ix_ai_job_history_provider"), table_name="ai_job_history")
    op.drop_column("ai_job_history", "finished_at")
    op.drop_column("ai_job_history", "started_at")
    op.drop_column("ai_job_history", "error")
    op.drop_column("ai_job_history", "retry_count")
    op.drop_column("ai_job_history", "cache_hit")
    op.drop_column("ai_job_history", "cost_usd")
    op.drop_column("ai_job_history", "total_tokens")
    op.drop_column("ai_job_history", "prompt_version")
    op.drop_column("ai_job_history", "task_type")
    op.drop_column("ai_job_history", "provider")
