"""add thumbnail telemetry

Revision ID: 004_add_thumbnail_telemetry
Revises: 003_add_thumbnail_source
Create Date: 2026-06-08 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "004_add_thumbnail_telemetry"
down_revision = "003_add_thumbnail_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns to processed_articles
    op.add_column("processed_articles", sa.Column("candidate_count", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("processed_articles", sa.Column("winner_pass", sa.String(length=50), nullable=True))
    op.add_column("processed_articles", sa.Column("selected_score", sa.Integer(), nullable=True))

    # Create thumbnail_decision_log table
    op.create_table(
        "thumbnail_decision_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("candidate_url", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("accepted", sa.Boolean(), server_default="false", nullable=True),
        sa.Column("rejection_reason", sa.String(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("aspect_ratio", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["processed_articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_thumbnail_decision_log_article_id"), "thumbnail_decision_log", ["article_id"], unique=False
    )
    op.create_index(op.f("ix_thumbnail_decision_log_id"), "thumbnail_decision_log", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_thumbnail_decision_log_id"), table_name="thumbnail_decision_log")
    op.drop_index(op.f("ix_thumbnail_decision_log_article_id"), table_name="thumbnail_decision_log")
    op.drop_table("thumbnail_decision_log")
    op.drop_column("processed_articles", "selected_score")
    op.drop_column("processed_articles", "winner_pass")
    op.drop_column("processed_articles", "candidate_count")
