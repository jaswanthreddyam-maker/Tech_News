"""thumbnail_pipeline

Revision ID: 24f31c800b13
Revises: d3545dd0daa0
Create Date: 2026-06-09 20:49:51.190616

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # revision identifiers, used by Alembic.

revision: str = "24f31c800b13"
down_revision: str | Sequence[str] | None = "d3545dd0daa0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("processed_articles", sa.Column("thumbnail_url", sa.Text(), nullable=True))
    op.add_column("processed_articles", sa.Column("thumbnail_local", sa.Text(), nullable=True))
    op.add_column(
        "processed_articles",
        sa.Column("thumbnail_status", sa.String(length=50), nullable=False, server_default="pending"),
    )
    op.add_column("processed_articles", sa.Column("thumbnail_hash", sa.String(length=64), nullable=True))
    op.add_column("processed_articles", sa.Column("thumbnail_source", sa.String(length=50), nullable=True))
    op.add_column("processed_articles", sa.Column("thumbnail_quality_score", sa.Integer(), nullable=True))
    op.add_column("processed_articles", sa.Column("candidate_count", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("processed_articles", sa.Column("winner_pass", sa.String(), nullable=True))
    op.add_column("processed_articles", sa.Column("selected_score", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("processed_articles", "selected_score")
    op.drop_column("processed_articles", "winner_pass")
    op.drop_column("processed_articles", "candidate_count")
    op.drop_column("processed_articles", "thumbnail_quality_score")
    op.drop_column("processed_articles", "thumbnail_source")
    op.drop_column("processed_articles", "thumbnail_hash")
    op.drop_column("processed_articles", "thumbnail_status")
    op.drop_column("processed_articles", "thumbnail_local")
    op.drop_column("processed_articles", "thumbnail_url")
