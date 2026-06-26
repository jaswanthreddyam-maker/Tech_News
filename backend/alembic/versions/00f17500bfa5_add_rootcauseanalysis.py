"""Add RootCauseAnalysis

Revision ID: 00f17500bfa5
Revises: 6b87a1e69554
Create Date: 2026-06-23 01:43:45.759344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '00f17500bfa5'
down_revision: Union[str, Sequence[str], None] = '6b87a1e69554'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'root_cause_analyses',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('correlation_id', sa.String(), nullable=False),
        sa.Column('timeline_id', sa.Integer(), sa.ForeignKey('root_cause_timelines.id'), nullable=True),
        sa.Column('root_cause', sa.String(), nullable=False),
        sa.Column('analysis_version', sa.String(), nullable=False, server_default='v1-rule-engine'),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('confidence_factors', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('generated_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_root_cause_analyses_correlation_id', 'root_cause_analyses', ['correlation_id'], unique=True)


def downgrade() -> None:
    op.drop_table('root_cause_analyses')
