"""Add last_processed_event_id to NewsletterReadModel

Revision ID: 89bad6d75e48
Revises: abe4169d6e4a
Create Date: 2026-06-23 10:30:48.405531

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '89bad6d75e48'
down_revision: Union[str, Sequence[str], None] = 'abe4169d6e4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('newsletter_stats_projection', sa.Column('last_processed_event_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('newsletter_stats_projection', 'last_processed_event_id')
