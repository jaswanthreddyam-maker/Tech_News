"""rename source to subscription_type

Revision ID: abe4169d6e4a
Revises: 3ce33590aa42
Create Date: 2026-06-23 10:18:38.699682

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'abe4169d6e4a'
down_revision: Union[str, Sequence[str], None] = '3ce33590aa42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('newsletter_subscribers', sa.Column('subscription_type', sa.String(), nullable=True))
    op.execute("UPDATE newsletter_subscribers SET subscription_type = source")
    op.drop_column('newsletter_subscribers', 'source')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('newsletter_subscribers', sa.Column('source', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.execute("UPDATE newsletter_subscribers SET source = subscription_type")
    op.drop_column('newsletter_subscribers', 'subscription_type')
