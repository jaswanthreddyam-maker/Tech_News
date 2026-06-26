"""Add RootCauseExplanation

Revision ID: 304d7ec808a7
Revises: 00f17500bfa5
Create Date: 2026-06-23 01:51:18.324143

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '304d7ec808a7'
down_revision: Union[str, Sequence[str], None] = '00f17500bfa5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'root_cause_explanations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('analysis_id', sa.Integer(), sa.ForeignKey('root_cause_analyses.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('generated_by', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

def downgrade() -> None:
    op.drop_table('root_cause_explanations')
