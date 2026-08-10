"""Add ingestion_cycle_metrics

Revision ID: 12341cb60600
Revises: c9f770a1578a
Create Date: 2026-08-10 11:17:59.413859

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '12341cb60600'
down_revision: Union[str, Sequence[str], None] = 'c9f770a1578a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('ingestion_cycle_metrics',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('sources_scanned', sa.Integer(), nullable=False),
    sa.Column('sources_crawled', sa.Integer(), nullable=False),
    sa.Column('articles_discovered', sa.Integer(), nullable=False),
    sa.Column('articles_saved', sa.Integer(), nullable=False),
    sa.Column('duplicates_skipped', sa.Integer(), nullable=False),
    sa.Column('filtered_skipped', sa.Integer(), nullable=False),
    sa.Column('failed_crawls', sa.Integer(), nullable=False),
    sa.Column('duration_seconds', sa.Float(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ingestion_cycle_metrics_id'), 'ingestion_cycle_metrics', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_ingestion_cycle_metrics_id'), table_name='ingestion_cycle_metrics')
    op.drop_table('ingestion_cycle_metrics')
