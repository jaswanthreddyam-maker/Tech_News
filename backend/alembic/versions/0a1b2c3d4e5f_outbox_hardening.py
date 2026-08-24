"""Outbox hardening: add max_retries, error_log, correlation_id columns to event_outbox
and create outbox_dispatch_checkpoints table for handler-level idempotency.

Revision ID: 0a1b2c3d4e5f
Revises: a9b8c7d6e5f4
Create Date: 2026-08-24 21:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0a1b2c3d4e5f'
down_revision: str | Sequence[str] | None = 'a9b8c7d6e5f4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add outbox hardening schema changes."""

    # --- EventOutbox: new columns ---
    op.add_column('event_outbox', sa.Column('max_retries', sa.Integer(), nullable=True, server_default='3'))
    op.add_column('event_outbox', sa.Column('error_log', sa.Text(), nullable=True))
    op.add_column('event_outbox', sa.Column('correlation_id', sa.String(length=255), nullable=True))

    # Add indexes for query performance
    op.create_index('ix_event_outbox_event_type', 'event_outbox', ['event_type'])
    op.create_index('ix_event_outbox_status', 'event_outbox', ['status'])
    op.create_index('ix_event_outbox_correlation_id', 'event_outbox', ['correlation_id'])

    # Add index on dead_letter_events.original_outbox_id for lookups
    op.create_index('ix_dead_letter_events_original_outbox_id', 'dead_letter_events', ['original_outbox_id'])

    # --- OutboxDispatchCheckpoint: new table ---
    op.create_table(
        'outbox_dispatch_checkpoints',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('handler_name', sa.String(length=100), nullable=False),
        sa.Column('outbox_event_id', sa.Integer(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['outbox_event_id'], ['event_outbox.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('handler_name', 'outbox_event_id', name='uq_dispatch_chkpt'),
    )
    op.create_index(
        'ix_dispatch_chkpt_lookup',
        'outbox_dispatch_checkpoints',
        ['handler_name', 'outbox_event_id'],
    )


def downgrade() -> None:
    """Reverse outbox hardening schema changes."""
    op.drop_table('outbox_dispatch_checkpoints')

    op.drop_index('ix_dead_letter_events_original_outbox_id', table_name='dead_letter_events')
    op.drop_index('ix_event_outbox_correlation_id', table_name='event_outbox')
    op.drop_index('ix_event_outbox_status', table_name='event_outbox')
    op.drop_index('ix_event_outbox_event_type', table_name='event_outbox')

    op.drop_column('event_outbox', 'correlation_id')
    op.drop_column('event_outbox', 'error_log')
    op.drop_column('event_outbox', 'max_retries')
