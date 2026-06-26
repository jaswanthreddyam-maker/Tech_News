"""initial_schema

Revision ID: 9a218bd768d1
Revises:
Create Date: 2026-06-09 20:49:32.413281

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op  # revision identifiers, used by Alembic.

revision: str = "9a218bd768d1"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_categories_id"), "categories", ["id"], unique=False)

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("method", sa.String(length=50), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("credibility_score", sa.Integer(), nullable=False),
        sa.Column("crawl_interval", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("health_state", sa.String(length=50), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("last_crawl_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column("parser_config", sa.String(), nullable=True),
        sa.Column("total_crawls", sa.Integer(), nullable=False),
        sa.Column("successful_crawls", sa.Integer(), nullable=False),
        sa.Column("reliability_score", sa.Numeric(), nullable=False),
        sa.Column("last_failure_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("url"),
    )
    op.create_index(op.f("ix_sources_id"), "sources", ["id"], unique=False)

    op.create_table(
        "raw_articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("url_hash", sa.String(length=64), nullable=False),
        sa.Column("title_hash", sa.String(length=64), nullable=False),
        sa.Column("compressed_html", sa.LargeBinary(), nullable=True),
        sa.Column("clean_text", sa.Text(), nullable=True),
        sa.Column("article_metadata", sa.Text(), nullable=True),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("html_refetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url_hash", "title_hash", name="uq_url_title_hash"),
    )
    op.create_index(op.f("ix_raw_articles_id"), "raw_articles", ["id"], unique=False)
    op.create_index(op.f("ix_raw_articles_status"), "raw_articles", ["status"], unique=False)
    op.create_index(op.f("ix_raw_articles_title_hash"), "raw_articles", ["title_hash"], unique=False)
    op.create_index(op.f("ix_raw_articles_url_hash"), "raw_articles", ["url_hash"], unique=False)

    op.create_table(
        "processed_articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("raw_article_id", sa.Integer(), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("source", sa.String(length=150), nullable=False),
        sa.Column("hero_image", sa.String(), nullable=True),
        sa.Column("source_name", sa.String(length=150), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("clean_html", sa.Text(), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("ai_confidence", sa.Numeric(), nullable=False),
        sa.Column("reading_time", sa.Integer(), nullable=False),
        sa.Column("published_status", sa.String(length=50), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False),
        sa.Column("seo_title", sa.String(length=255), nullable=True),
        sa.Column("seo_keywords", sa.Text(), nullable=True),
        sa.Column("readability_score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("impact_score", sa.Numeric(), nullable=False),
        sa.Column("freshness_score", sa.Numeric(), nullable=False),
        sa.Column("engagement_score", sa.Numeric(), nullable=False),
        sa.Column("final_score", sa.Numeric(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["raw_article_id"], ["raw_articles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_processed_articles_id"), "processed_articles", ["id"], unique=False)
    op.create_index(
        op.f("ix_processed_articles_published_status"), "processed_articles", ["published_status"], unique=False
    )
    op.create_index(op.f("ix_processed_articles_slug"), "processed_articles", ["slug"], unique=True)

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_topics_id"), "topics", ["id"], unique=False)

    op.create_table(
        "topic_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_topic_aliases_alias"), "topic_aliases", ["alias"], unique=True)
    op.create_index(op.f("ix_topic_aliases_id"), "topic_aliases", ["id"], unique=False)

    op.create_table(
        "trending_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("topic"),
    )
    op.create_index(op.f("ix_trending_topics_id"), "trending_topics", ["id"], unique=False)

    op.create_table(
        "agent_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_logs_agent_name"), "agent_logs", ["agent_name"], unique=False)
    op.create_index(op.f("ix_agent_logs_id"), "agent_logs", ["id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_agent_logs_id"), table_name="agent_logs")
    op.drop_index(op.f("ix_agent_logs_agent_name"), table_name="agent_logs")
    op.drop_table("agent_logs")
    op.drop_index(op.f("ix_trending_topics_id"), table_name="trending_topics")
    op.drop_table("trending_topics")
    op.drop_index(op.f("ix_topic_aliases_id"), table_name="topic_aliases")
    op.drop_index(op.f("ix_topic_aliases_alias"), table_name="topic_aliases")
    op.drop_table("topic_aliases")
    op.drop_index(op.f("ix_topics_id"), table_name="topics")
    op.drop_table("topics")

    op.drop_index(op.f("ix_processed_articles_slug"), table_name="processed_articles")
    op.drop_index(op.f("ix_processed_articles_published_status"), table_name="processed_articles")
    op.drop_index(op.f("ix_processed_articles_id"), table_name="processed_articles")
    op.drop_table("processed_articles")

    op.drop_index(op.f("ix_raw_articles_url_hash"), table_name="raw_articles")
    op.drop_index(op.f("ix_raw_articles_title_hash"), table_name="raw_articles")
    op.drop_index(op.f("ix_raw_articles_status"), table_name="raw_articles")
    op.drop_index(op.f("ix_raw_articles_id"), table_name="raw_articles")
    op.drop_table("raw_articles")

    op.drop_index(op.f("ix_sources_id"), table_name="sources")
    op.drop_table("sources")

    op.drop_index(op.f("ix_categories_id"), table_name="categories")
    op.drop_table("categories")
