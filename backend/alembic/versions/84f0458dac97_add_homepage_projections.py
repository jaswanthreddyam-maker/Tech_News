"""Add homepage_projections

Revision ID: 84f0458dac97
Revises: 25de4c55dc3f
Create Date: 2026-08-07 21:44:07.141364

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '84f0458dac97'
down_revision: Union[str, Sequence[str], None] = '25de4c55dc3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('homepage_projections',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('projection_version', sa.Integer(), nullable=False),
    sa.Column('ranking_version', sa.String(length=32), nullable=False),
    sa.Column('pipeline_version', sa.String(length=32), nullable=False),
    sa.Column('generated_by', sa.String(length=64), nullable=False),
    sa.Column('stories_json', sa.JSON(), nullable=False),
    sa.Column('explanation_json', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_homepage_projections'))
    )
    op.create_index(op.f('ix_homepage_projections_projection_version'), 'homepage_projections', ['projection_version'], unique=False)
    op.create_index(op.f('ix_homepage_projections_created_at'), 'homepage_projections', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_homepage_projections_created_at'), table_name='homepage_projections')
    op.drop_index(op.f('ix_homepage_projections_projection_version'), table_name='homepage_projections')
    op.drop_table('homepage_projections')
