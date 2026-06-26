"""add_thumbnail_observability_fields

Revision ID: f3b610c14c50
Revises: 77362901f448
Create Date: 2026-06-20 22:55:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f3b610c14c50'
down_revision: str | Sequence[str] | None = '77362901f448'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_score INTEGER')
    op.execute('ALTER TABLE processed_articles ADD COLUMN IF NOT EXISTS thumbnail_algorithm_version VARCHAR(50)')
    op.execute('ALTER TABLE thumbnail_decision_log ADD COLUMN IF NOT EXISTS candidate_score INTEGER')
    op.execute('ALTER TABLE thumbnail_decision_log ADD COLUMN IF NOT EXISTS candidate_status VARCHAR(50)')
    op.execute('ALTER TABLE thumbnail_decision_log ADD COLUMN IF NOT EXISTS algorithm_version VARCHAR(50)')

def downgrade() -> None:
    """Downgrade schema."""
    op.execute('ALTER TABLE thumbnail_decision_log DROP COLUMN IF EXISTS algorithm_version')
    op.execute('ALTER TABLE thumbnail_decision_log DROP COLUMN IF EXISTS candidate_status')
    op.execute('ALTER TABLE thumbnail_decision_log DROP COLUMN IF EXISTS candidate_score')
    op.execute('ALTER TABLE processed_articles DROP COLUMN IF EXISTS thumbnail_algorithm_version')
    op.execute('ALTER TABLE processed_articles DROP COLUMN IF EXISTS thumbnail_score')
