"""Add Recovery Ledger and Timeline

Revision ID: 6b87a1e69554
Revises: 660ff4da4ffc
Create Date: 2026-06-23 01:35:35.548125

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '6b87a1e69554'
down_revision: Union[str, Sequence[str], None] = '660ff4da4ffc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. TimelineNodeType ENUM
    op.execute("CREATE TYPE timeline_node_type AS ENUM ('EVENT', 'METRIC', 'HEALTH_CHECK', 'RECOVERY', 'ALERT', 'AI_DECISION')")

    # 2. recovery_execution_logs
    op.create_table(
        'recovery_execution_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('recovery_id', sa.String(), nullable=False),
        sa.Column('policy_name', sa.String(), nullable=False),
        sa.Column('trigger_reason', sa.Text(), nullable=False),
        sa.Column('mode', sa.String(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('correlation_id', sa.String(), nullable=False)
    )
    op.create_index('ix_recovery_execution_logs_recovery_id', 'recovery_execution_logs', ['recovery_id'], unique=True)
    op.create_index('ix_recovery_execution_logs_policy_name', 'recovery_execution_logs', ['policy_name'])
    op.create_index('ix_recovery_execution_logs_correlation_id', 'recovery_execution_logs', ['correlation_id'])

    # 3. timeline_nodes
    op.create_table(
        'timeline_nodes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('correlation_id', sa.String(), nullable=False),
        sa.Column('node_type', postgresql.ENUM('EVENT', 'METRIC', 'HEALTH_CHECK', 'RECOVERY', 'ALERT', 'AI_DECISION', name='timeline_node_type', create_type=False), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('caused_by_id', sa.Integer(), sa.ForeignKey('timeline_nodes.id'), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.create_index('ix_timeline_nodes_correlation_id', 'timeline_nodes', ['correlation_id'])

    # 4. root_cause_timelines
    op.create_table(
        'root_cause_timelines',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('correlation_id', sa.String(), nullable=False),
        sa.Column('root_event_id', sa.Integer(), sa.ForeignKey('timeline_nodes.id'), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='unresolved'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_root_cause_timelines_correlation_id', 'root_cause_timelines', ['correlation_id'], unique=True)


def downgrade() -> None:
    op.drop_table('root_cause_timelines')
    op.drop_table('timeline_nodes')
    op.drop_table('recovery_execution_logs')
    op.execute("DROP TYPE timeline_node_type")
