"""add_editorial_intelligence

Revision ID: c64e3c221afe
Revises: f3b610c14c50
Create Date: 2026-06-21 02:16:18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c64e3c221afe'
down_revision: Union[str, Sequence[str], None] = 'f3b610c14c50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add columns to processed_articles table
    op.add_column('processed_articles', sa.Column('editorial_version', sa.String(length=50), nullable=True))
    op.add_column('processed_articles', sa.Column('enrichment_status', sa.String(length=50), nullable=False, server_default='pending'))
    op.add_column('processed_articles', sa.Column('completed_enrichment_stages', sa.JSON(), nullable=False, server_default='[]'))
    
    # Make impact_score on processed_articles nullable
    op.alter_column('processed_articles', 'impact_score', existing_type=sa.Numeric(), nullable=True)

    # 2. Rename importance_score to impact_score in articles table
    op.alter_column('articles', 'importance_score', new_column_name='impact_score', existing_type=sa.Numeric(), nullable=True)

    # 3. Create tnt_editorial_decision_logs table
    op.create_table(
        'tnt_editorial_decision_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('snapshot_id', sa.String(length=64), nullable=False),
        sa.Column('article_id', sa.String(length=64), nullable=False),
        sa.Column('impact_score', sa.Numeric(), nullable=False),
        sa.Column('freshness_multiplier', sa.Numeric(), nullable=False),
        sa.Column('effective_score', sa.Numeric(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('ranking_position', sa.Integer(), nullable=False),
        sa.Column('algorithm_version', sa.String(length=50), nullable=False),
        sa.Column('selection_reason_code', sa.String(length=50), nullable=False),
        sa.Column('selection_reason_details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tnt_editorial_decision_logs_id'), 'tnt_editorial_decision_logs', ['id'], unique=False)
    op.create_index(op.f('ix_tnt_editorial_decision_logs_snapshot_id'), 'tnt_editorial_decision_logs', ['snapshot_id'], unique=False)
    op.create_index(op.f('ix_tnt_editorial_decision_logs_article_id'), 'tnt_editorial_decision_logs', ['article_id'], unique=False)


def downgrade() -> None:
    # Drop index and table
    op.drop_index(op.f('ix_tnt_editorial_decision_logs_article_id'), table_name='tnt_editorial_decision_logs')
    op.drop_index(op.f('ix_tnt_editorial_decision_logs_snapshot_id'), table_name='tnt_editorial_decision_logs')
    op.drop_index(op.f('ix_tnt_editorial_decision_logs_id'), table_name='tnt_editorial_decision_logs')
    op.drop_table('tnt_editorial_decision_logs')

    # Rename impact_score back to importance_score in articles
    op.alter_column('articles', 'impact_score', new_column_name='importance_score', existing_type=sa.Numeric(), nullable=False, server_default='0.0')

    # Make impact_score on processed_articles non-nullable (default 0.0)
    op.alter_column('processed_articles', 'impact_score', existing_type=sa.Numeric(), nullable=False, server_default='0.0')

    # Drop columns from processed_articles
    op.drop_column('processed_articles', 'completed_enrichment_stages')
    op.drop_column('processed_articles', 'enrichment_status')
    op.drop_column('processed_articles', 'editorial_version')
