"""telemetry

Revision ID: 6f679dff3088
Revises: 24f31c800b13
Create Date: 2026-06-09 20:49:58.227822

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # revision identifiers, used by Alembic.

revision: str = "6f679dff3088"
down_revision: str | Sequence[str] | None = "24f31c800b13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "thumbnail_decision_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("candidate_url", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=True),
        sa.Column("rejection_reason", sa.String(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("aspect_ratio", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["processed_articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_thumbnail_decision_log_article_id"), "thumbnail_decision_log", ["article_id"], unique=False
    )
    op.create_index(op.f("ix_thumbnail_decision_log_id"), "thumbnail_decision_log", ["id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_thumbnail_decision_log_id"), table_name="thumbnail_decision_log")
    op.drop_index(op.f("ix_thumbnail_decision_log_article_id"), table_name="thumbnail_decision_log")
    op.drop_table("thumbnail_decision_log")
