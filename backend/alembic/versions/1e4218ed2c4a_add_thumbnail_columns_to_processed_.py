"""Add thumbnail columns to processed_articles manually

Revision ID: 1e4218ed2c4a
Revises: 25e518b3a2db
Create Date: 2026-06-20 16:20:19.629328

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1e4218ed2c4a'
down_revision: str | Sequence[str] | None = '25e518b3a2db'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_url TEXT')
    op.execute('ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_local TEXT')
    op.execute('ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_status VARCHAR(50)')
    op.execute('ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_hash VARCHAR(64)')
    op.execute('ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_source VARCHAR(50)')
    op.execute('ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_quality_score INTEGER')
    op.execute('ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS candidate_count INTEGER')
    op.execute('ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS winner_pass VARCHAR')
    op.execute('ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS selected_score INTEGER')

def downgrade() -> None:
    """Downgrade schema."""
    op.execute('ALTER TABLE processed_articles DROP COLUMN IF EXISTS selected_score')
    op.execute('ALTER TABLE processed_articles DROP COLUMN IF EXISTS winner_pass')
    op.execute('ALTER TABLE processed_articles DROP COLUMN IF EXISTS candidate_count')
    op.execute('ALTER TABLE processed_articles DROP COLUMN IF EXISTS thumbnail_quality_score')
    op.execute('ALTER TABLE processed_articles DROP COLUMN IF EXISTS thumbnail_source')
    op.execute('ALTER TABLE processed_articles DROP COLUMN IF EXISTS thumbnail_hash')
    op.execute('ALTER TABLE processed_articles DROP COLUMN IF EXISTS thumbnail_status')
    op.execute('ALTER TABLE processed_articles DROP COLUMN IF EXISTS thumbnail_local')
    op.execute('ALTER TABLE processed_articles DROP COLUMN IF EXISTS thumbnail_url')
