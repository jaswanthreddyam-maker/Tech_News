"""add article expiration fields

Revision ID: d17f2a77e24c
Revises: 7ee8081fe89e
Create Date: 2026-08-11 19:48:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d17f2a77e24c"
down_revision = "7ee8081fe89e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "processed_articles",
        sa.Column("is_expired", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "processed_articles",
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_processed_articles_is_expired",
        "processed_articles",
        ["is_expired"],
    )


def downgrade() -> None:
    op.drop_index("idx_processed_articles_is_expired", table_name="processed_articles")
    op.drop_column("processed_articles", "expired_at")
    op.drop_column("processed_articles", "is_expired")
