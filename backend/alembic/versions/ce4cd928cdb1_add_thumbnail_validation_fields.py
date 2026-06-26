"""add_thumbnail_validation_fields

Revision ID: ce4cd928cdb1
Revises: d71685bc4595
Create Date: 2026-06-12 18:33:07.504031

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ce4cd928cdb1"
down_revision: str | Sequence[str] | None = "d71685bc4595"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "processed_articles", sa.Column("thumbnail_last_verified_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("processed_articles", sa.Column("thumbnail_content_type", sa.String(length=100), nullable=True))
    op.add_column("processed_articles", sa.Column("thumbnail_width", sa.Integer(), nullable=True))
    op.add_column("processed_articles", sa.Column("thumbnail_height", sa.Integer(), nullable=True))
    op.drop_column("processed_articles", "thumbnail_status")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "processed_articles",
        sa.Column("thumbnail_status", sa.String(length=50), server_default="pending", nullable=True),
    )
    op.drop_column("processed_articles", "thumbnail_height")
    op.drop_column("processed_articles", "thumbnail_width")
    op.drop_column("processed_articles", "thumbnail_content_type")
    op.drop_column("processed_articles", "thumbnail_last_verified_at")
