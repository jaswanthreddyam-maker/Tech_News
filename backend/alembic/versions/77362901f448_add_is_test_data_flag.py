"""add is_test_data flag

Revision ID: 77362901f448
Revises: 1e4218ed2c4a
Create Date: 2026-06-20 18:40:22.321691

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '77362901f448'
down_revision: str | Sequence[str] | None = '1e4218ed2c4a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('raw_articles', sa.Column('is_test_data', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('processed_articles', sa.Column('is_test_data', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('articles', sa.Column('is_test_data', sa.Boolean(), server_default='false', nullable=False))

    op.create_index(op.f('ix_raw_articles_is_test_data'), 'raw_articles', ['is_test_data'], unique=False)
    op.create_index(op.f('ix_processed_articles_is_test_data'), 'processed_articles', ['is_test_data'], unique=False)
    op.create_index(op.f('ix_articles_is_test_data'), 'articles', ['is_test_data'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_articles_is_test_data'), table_name='articles')
    op.drop_index(op.f('ix_processed_articles_is_test_data'), table_name='processed_articles')
    op.drop_index(op.f('ix_raw_articles_is_test_data'), table_name='raw_articles')

    op.drop_column('articles', 'is_test_data')
    op.drop_column('processed_articles', 'is_test_data')
    op.drop_column('raw_articles', 'is_test_data')
