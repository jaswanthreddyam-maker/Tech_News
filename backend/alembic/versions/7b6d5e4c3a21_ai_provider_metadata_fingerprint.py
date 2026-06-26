"""ai provider metadata fingerprint

Revision ID: 7b6d5e4c3a21
Revises: 3f7c2b1a9d4e
Create Date: 2026-06-10 18:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # revision identifiers, used by Alembic.

revision: str = "7b6d5e4c3a21"
down_revision: str | Sequence[str] | None = "3f7c2b1a9d4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "ai_job_history",
        sa.Column("provider_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "ai_job_history",
        sa.Column("enrichment_input_fingerprint", sa.String(length=64), nullable=True),
    )
    op.create_index(
        op.f("ix_ai_job_history_enrichment_input_fingerprint"),
        "ai_job_history",
        ["enrichment_input_fingerprint"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_ai_job_history_enrichment_input_fingerprint"), table_name="ai_job_history")
    op.drop_column("ai_job_history", "enrichment_input_fingerprint")
    op.drop_column("ai_job_history", "provider_metadata")
