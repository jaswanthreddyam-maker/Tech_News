"""Editorial Dashboard Hardening

Revision ID: 8561a227444b
Revises: 67e18a9a9f83
Create Date: 2026-06-23 16:11:03.139450

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8561a227444b'
down_revision: Union[str, Sequence[str], None] = '67e18a9a9f83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('newsletter_campaign_analytics', sa.Column('unsubscribe_rate', sa.String(), nullable=False, server_default='0.00'))
    op.add_column('newsletter_campaigns', sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint('uq_newsletter_campaign_briefing', 'newsletter_campaigns', ['briefing_id'])

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_newsletter_campaign_briefing', 'newsletter_campaigns', type_='unique')
    op.drop_column('newsletter_campaigns', 'scheduled_at')
    op.drop_column('newsletter_campaign_analytics', 'unsubscribe_rate')
