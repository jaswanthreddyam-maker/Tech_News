"""Add filter_reason to RawArticle

Revision ID: c9f770a1578a
Revises: briefing_v1_schema
Create Date: 2026-08-10 11:13:22.335003

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c9f770a1578a'
down_revision: Union[str, Sequence[str], None] = 'briefing_v1_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('raw_articles', sa.Column('filter_reason', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('raw_articles', 'filter_reason')
