"""Add thumbnail columns to ArticleReadModel

Revision ID: 25e518b3a2db
Revises: 699875afef73
Create Date: 2026-06-20 16:04:23.467094

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '25e518b3a2db'
down_revision: str | Sequence[str] | None = '699875afef73'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('articles', sa.Column('thumbnail_url', sa.String(), nullable=True))
    op.add_column('articles', sa.Column('thumbnail_local', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('articles', 'thumbnail_local')
    op.drop_column('articles', 'thumbnail_url')
