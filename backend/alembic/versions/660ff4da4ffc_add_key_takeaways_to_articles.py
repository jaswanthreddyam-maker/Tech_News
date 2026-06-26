"""add_key_takeaways_to_articles

Revision ID: 660ff4da4ffc
Revises: c64e3c221afe
Create Date: 2026-06-21 08:47:44.506296

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '660ff4da4ffc'
down_revision: Union[str, Sequence[str], None] = 'c64e3c221afe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('processed_articles', sa.Column('key_takeaways', sa.JSON(), nullable=True))
    op.add_column('articles', sa.Column('key_takeaways', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('articles', 'key_takeaways')
    op.drop_column('processed_articles', 'key_takeaways')

