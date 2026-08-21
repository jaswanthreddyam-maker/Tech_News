"""Add followed_sources table, source slug/description/logo_url, and query indexes

Revision ID: a9b8c7d6e5f4
Revises: d17f2a77e24c
Create Date: 2026-08-21 08:50:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a9b8c7d6e5f4'
down_revision: str | Sequence[str] | None = 'd17f2a77e24c'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add slug, description, logo_url to sources
    op.add_column('sources', sa.Column('slug', sa.String(length=100), nullable=True))
    op.add_column('sources', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('sources', sa.Column('logo_url', sa.String(length=500), nullable=True))
    op.create_index(op.f('ix_sources_slug'), 'sources', ['slug'], unique=True)

    # 2. Create followed_sources table
    op.create_table(
        'followed_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('followed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'source_id', name='uq_followed_source'),
    )
    op.create_index(op.f('ix_followed_sources_id'), 'followed_sources', ['id'], unique=False)
    op.create_index(op.f('ix_followed_sources_user_id'), 'followed_sources', ['user_id'], unique=False)
    op.create_index(op.f('ix_followed_sources_source_id'), 'followed_sources', ['source_id'], unique=False)

    # 3. Create composite index on processed_articles for fast source following feed resolution
    op.create_index(
        'ix_processed_articles_source_published',
        'processed_articles',
        ['source_id', sa.text('published_at DESC')],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_processed_articles_source_published', table_name='processed_articles')
    op.drop_index(op.f('ix_followed_sources_source_id'), table_name='followed_sources')
    op.drop_index(op.f('ix_followed_sources_user_id'), table_name='followed_sources')
    op.drop_index(op.f('ix_followed_sources_id'), table_name='followed_sources')
    op.drop_table('followed_sources')
    op.drop_index(op.f('ix_sources_slug'), table_name='sources')
    op.drop_column('sources', 'logo_url')
    op.drop_column('sources', 'description')
    op.drop_column('sources', 'slug')
