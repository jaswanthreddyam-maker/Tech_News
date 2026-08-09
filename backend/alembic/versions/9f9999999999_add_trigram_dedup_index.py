"""add trigram dedup index

Revision ID: 9f9999999999
Revises: rc4_activation_001
Create Date: 2026-08-07 06:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f9999999999'
down_revision: Union[str, None] = 'rc4_activation_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_raw_articles_title_trgm ON raw_articles USING gin (title gin_trgm_ops);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_raw_articles_title_trgm;")
