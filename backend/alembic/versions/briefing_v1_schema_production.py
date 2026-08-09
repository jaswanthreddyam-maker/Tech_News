"""daily_briefing_v1_schema_production

Revision ID: briefing_v1_schema
Revises: rc4_activation_001, 84f0458dac97
Create Date: 2026-08-09 11:30:00

"""
from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'briefing_v1_schema'
down_revision: Union[str, Sequence[str], None] = ('rc4_activation_001', '84f0458dac97')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. daily_briefing_subscribers
    op.execute("""
    CREATE TABLE IF NOT EXISTS daily_briefing_subscribers (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        email VARCHAR(255) NOT NULL UNIQUE,
        preferred_time VARCHAR(10) NOT NULL DEFAULT '08:00',
        timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
        story_count INTEGER NOT NULL DEFAULT 5,
        topics JSONB,
        enabled BOOLEAN NOT NULL DEFAULT TRUE,
        email_verified_at TIMESTAMP WITH TIME ZONE,
        verification_token_hash VARCHAR(128),
        verification_sent_at TIMESTAMP WITH TIME ZONE,
        unsubscribe_token_hash VARCHAR(128),
        unsubscribed_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_daily_briefing_subscribers_email ON daily_briefing_subscribers(email);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_daily_briefing_subscribers_user_id ON daily_briefing_subscribers(user_id);")

    # 2. daily_briefing_editions
    op.execute("""
    CREATE TABLE IF NOT EXISTS daily_briefing_editions (
        id SERIAL PRIMARY KEY,
        edition_date DATE NOT NULL UNIQUE,
        algorithm_version VARCHAR(20) NOT NULL DEFAULT 'v1',
        topic_snapshot JSONB,
        generated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_daily_briefing_editions_date ON daily_briefing_editions(edition_date);")

    # 3. daily_briefing_items
    op.execute("""
    CREATE TABLE IF NOT EXISTS daily_briefing_items (
        id SERIAL PRIMARY KEY,
        edition_id INTEGER NOT NULL REFERENCES daily_briefing_editions(id) ON DELETE CASCADE,
        article_id VARCHAR(255) NOT NULL,
        cluster_id VARCHAR(255),
        rank INTEGER NOT NULL,
        headline VARCHAR(500) NOT NULL,
        why_it_matters TEXT NOT NULL,
        category VARCHAR(100) NOT NULL,
        source VARCHAR(255),
        url TEXT,
        read_time INTEGER NOT NULL DEFAULT 3,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_briefing_item_rank UNIQUE (edition_id, rank)
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_daily_briefing_items_edition ON daily_briefing_items(edition_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_daily_briefing_items_article ON daily_briefing_items(article_id);")

    # 4. daily_briefing_deliveries
    op.execute("""
    CREATE TABLE IF NOT EXISTS daily_briefing_deliveries (
        id SERIAL PRIMARY KEY,
        edition_id INTEGER NOT NULL REFERENCES daily_briefing_editions(id) ON DELETE CASCADE,
        subscriber_id INTEGER NOT NULL REFERENCES daily_briefing_subscribers(id) ON DELETE CASCADE,
        status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
        provider VARCHAR(50) NOT NULL DEFAULT 'RESEND',
        provider_message_id VARCHAR(255),
        opened_observed_at TIMESTAMP WITH TIME ZONE,
        first_clicked_at TIMESTAMP WITH TIME ZONE,
        click_count INTEGER NOT NULL DEFAULT 0,
        provider_clicked_at TIMESTAMP WITH TIME ZONE,
        stories_delivered INTEGER NOT NULL DEFAULT 5,
        scheduled_for TIMESTAMP WITH TIME ZONE,
        sent_at TIMESTAMP WITH TIME ZONE,
        delivered_at TIMESTAMP WITH TIME ZONE,
        bounced_at TIMESTAMP WITH TIME ZONE,
        error_message TEXT,
        retry_count INTEGER NOT NULL DEFAULT 0,
        idempotency_key VARCHAR(128) UNIQUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_sub_edition UNIQUE (subscriber_id, edition_id)
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_daily_briefing_deliveries_subscriber ON daily_briefing_deliveries(subscriber_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_daily_briefing_deliveries_edition ON daily_briefing_deliveries(edition_id);")

    # 5. daily_briefing_delivery_events
    op.execute("""
    CREATE TABLE IF NOT EXISTS daily_briefing_delivery_events (
        id SERIAL PRIMARY KEY,
        delivery_id INTEGER NOT NULL REFERENCES daily_briefing_deliveries(id) ON DELETE CASCADE,
        event_type VARCHAR(50) NOT NULL,
        payload JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_daily_briefing_events_delivery ON daily_briefing_delivery_events(delivery_id);")

    # 6. webhook_events
    op.execute("""
    CREATE TABLE IF NOT EXISTS webhook_events (
        id SERIAL PRIMARY KEY,
        provider VARCHAR(50) NOT NULL,
        event_id VARCHAR(255) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        payload_hash VARCHAR(64) NOT NULL,
        processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT uq_provider_event UNIQUE (provider, event_id)
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_webhook_events_provider_event ON webhook_events(provider, event_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS webhook_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS daily_briefing_delivery_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS daily_briefing_deliveries CASCADE;")
    op.execute("DROP TABLE IF EXISTS daily_briefing_items CASCADE;")
    op.execute("DROP TABLE IF EXISTS daily_briefing_editions CASCADE;")
    op.execute("DROP TABLE IF EXISTS daily_briefing_subscribers CASCADE;")
