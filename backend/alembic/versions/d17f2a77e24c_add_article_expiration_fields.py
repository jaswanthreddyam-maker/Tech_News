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
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('processed_articles')]
    if 'is_expired' not in columns:
        op.add_column(
            "processed_articles",
            sa.Column("is_expired", sa.Boolean(), server_default="false", nullable=False),
        )
    if 'expired_at' not in columns:
        op.add_column(
            "processed_articles",
            sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        )
    indexes = [idx['name'] for idx in inspector.get_indexes('processed_articles')]
    if 'idx_processed_articles_is_expired' not in indexes:
        op.create_index(
            "idx_processed_articles_is_expired",
            "processed_articles",
            ["is_expired"],
        )


def downgrade() -> None:
    op.drop_index("idx_processed_articles_is_expired", table_name="processed_articles")
    op.drop_column("processed_articles", "expired_at")
    op.drop_column("processed_articles", "is_expired")
