"""add homepage projections

Revision ID: 9f9999999998
Revises: 9f9999999999
Create Date: 2026-08-07 06:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f9999999998'
down_revision: Union[str, None] = '9f9999999999'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS homepage_projections (
            id VARCHAR(36) PRIMARY KEY,
            projection_version INTEGER NOT NULL,
            stories_json JSONB NOT NULL,
            explanation_json JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_homepage_projections_created_at ON homepage_projections(created_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS homepage_projections;")
