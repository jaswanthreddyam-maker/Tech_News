"""Update UserInterest schema

Revision ID: 88e0782ea87f
Revises: e6bad02e4ff8
Create Date: 2026-06-14 10:48:46.367164

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '88e0782ea87f'
down_revision: str | Sequence[str] | None = 'e6bad02e4ff8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Upgrade schema
    op.add_column('user_interests', sa.Column('affinity', sa.Float(), nullable=True))
    op.add_column('user_interests', sa.Column('expertise', sa.Float(), nullable=True))
    op.add_column('user_interests', sa.Column('model_version', sa.String(length=20), nullable=True))

    op.execute('UPDATE user_interests SET affinity = score, expertise = 0.0, model_version = \'v1\'')

    op.alter_column('user_interests', 'affinity', existing_type=sa.Float(), nullable=False)
    op.alter_column('user_interests', 'expertise', existing_type=sa.Float(), nullable=False)
    op.alter_column('user_interests', 'model_version', existing_type=sa.String(length=20), nullable=False)

    op.drop_column('user_interests', 'score')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('user_interests', sa.Column('score', sa.Float(), nullable=True))
    op.execute('UPDATE user_interests SET score = affinity')
    op.alter_column('user_interests', 'score', existing_type=sa.Float(), nullable=False)

    op.drop_column('user_interests', 'model_version')
    op.drop_column('user_interests', 'expertise')
    op.drop_column('user_interests', 'affinity')
