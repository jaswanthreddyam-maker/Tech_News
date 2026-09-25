"""Ensure homepage_projections and category_desk_projections tables exist.

Revision ID: 2c3d4e5f6a7b
Revises: 1b2c3d4e5f6a
Create Date: 2026-09-25 08:15:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2c3d4e5f6a7b'
down_revision: str | Sequence[str] | None = '1b2c3d4e5f6a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create homepage_projections and category_desk_projections if not already present."""
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS homepage_projections (
            id VARCHAR(36) PRIMARY KEY,
            projection_version INTEGER NOT NULL,
            ranking_version VARCHAR(32) NOT NULL DEFAULT '2.1',
            pipeline_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
            generated_by VARCHAR(64) NOT NULL DEFAULT 'HomepageBuilder',
            stories_json JSON NOT NULL,
            explanation_json JSON,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_homepage_projections_projection_version ON homepage_projections (projection_version)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_homepage_projections_created_at ON homepage_projections (created_at DESC)"))

    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS category_desk_projections (
            id VARCHAR(36) PRIMARY KEY,
            category_slug VARCHAR(64) NOT NULL,
            article_count INTEGER NOT NULL DEFAULT 0,
            article_ids JSON NOT NULL,
            projection_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
            algorithm_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
            policy_version VARCHAR(32) NOT NULL DEFAULT '1.0.0',
            build_duration_ms INTEGER NOT NULL DEFAULT 0,
            rebuilt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_category_desk_projections_category_slug ON category_desk_projections (category_slug)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_category_desk_projections_created_at ON category_desk_projections (created_at DESC)"))


def downgrade() -> None:
    """Drop projection tables."""
    op.execute(sa.text("DROP TABLE IF EXISTS category_desk_projections CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS homepage_projections CASCADE"))
