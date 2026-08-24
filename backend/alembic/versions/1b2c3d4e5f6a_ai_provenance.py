"""AI provenance: create ai_inference_records table and add inference_id FK
to tnt_article_entities and tnt_relationship_edges.

Revision ID: 1b2c3d4e5f6a
Revises: 0a1b2c3d4e5f
Create Date: 2026-08-24 21:25:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1b2c3d4e5f6a'
down_revision: str | Sequence[str] | None = '0a1b2c3d4e5f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add AI provenance infrastructure."""

    # --- AIInferenceRecord table ---
    op.create_table(
        'ai_inference_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_article_id', sa.Integer(), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('prompt_version', sa.String(length=50), nullable=False),
        sa.Column('prompt_hash', sa.String(length=64), nullable=False),
        sa.Column('input_fingerprint', sa.String(length=64), nullable=True),
        sa.Column('job_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['source_article_id'], ['processed_articles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['job_id'], ['ai_job_history.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_ai_inference_records_source_article_id', 'ai_inference_records', ['source_article_id'])
    op.create_index('ix_ai_inference_records_provider', 'ai_inference_records', ['provider'])
    op.create_index('ix_ai_inference_records_task_type', 'ai_inference_records', ['task_type'])
    op.create_index('ix_ai_inference_records_input_fingerprint', 'ai_inference_records', ['input_fingerprint'])

    # --- Add inference_id FK to tnt_article_entities ---
    op.add_column(
        'tnt_article_entities',
        sa.Column('inference_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_article_entity_inference',
        'tnt_article_entities',
        'ai_inference_records',
        ['inference_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_tnt_article_entities_inference_id', 'tnt_article_entities', ['inference_id'])

    # --- Add inference_id FK to tnt_relationship_edges ---
    op.add_column(
        'tnt_relationship_edges',
        sa.Column('inference_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_relationship_edge_inference',
        'tnt_relationship_edges',
        'ai_inference_records',
        ['inference_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_tnt_relationship_edges_inference_id', 'tnt_relationship_edges', ['inference_id'])


def downgrade() -> None:
    """Reverse AI provenance schema changes."""
    op.drop_index('ix_tnt_relationship_edges_inference_id', table_name='tnt_relationship_edges')
    op.drop_constraint('fk_relationship_edge_inference', 'tnt_relationship_edges', type_='foreignkey')
    op.drop_column('tnt_relationship_edges', 'inference_id')

    op.drop_index('ix_tnt_article_entities_inference_id', table_name='tnt_article_entities')
    op.drop_constraint('fk_article_entity_inference', 'tnt_article_entities', type_='foreignkey')
    op.drop_column('tnt_article_entities', 'inference_id')

    op.drop_table('ai_inference_records')
