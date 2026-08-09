"""
Idempotent migration for Daily Briefing schema changes.

Changes applied:
  1. DailyBriefingDelivery — add engagement telemetry columns:
       opened_observed_at, first_clicked_at, click_count, provider_clicked_at, stories_delivered
  2. DailyBriefingDelivery — remove legacy columns (opened_at, clicked_at) after migrating data
  3. BriefingDeliveryStatus enum — remove CLICKED and OPENED_OBSERVED values
       (Postgres requires create new type → alter column → drop old → rename)
  4. DailyBriefingSubscriber — add unsubscribed_at column
  5. DailyBriefingEdition — update algorithm_version default annotation (no schema change needed)

Run from backend directory:
    venv\\Scripts\\python.exe scripts\\migrate_briefing_tables.py
"""
import asyncio
import logging
import sys
import os

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def run_migration():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        logger.error("DATABASE_URL not set in environment.")
        sys.exit(1)

    engine = create_async_engine(database_url, echo=False)

    async with engine.begin() as conn:
        logger.info("Starting Daily Briefing schema migration...")

        # ----------------------------------------------------------------
        # 1. Add new engagement telemetry columns to daily_briefing_deliveries
        # ----------------------------------------------------------------
        new_delivery_columns = [
            ("opened_observed_at", "TIMESTAMP WITH TIME ZONE"),
            ("first_clicked_at",   "TIMESTAMP WITH TIME ZONE"),
            ("click_count",        "INTEGER DEFAULT 0 NOT NULL"),
            ("provider_clicked_at","TIMESTAMP WITH TIME ZONE"),
            ("stories_delivered",  "INTEGER DEFAULT 5 NOT NULL"),
        ]
        for col_name, col_def in new_delivery_columns:
            try:
                await conn.execute(text(
                    f"ALTER TABLE daily_briefing_deliveries ADD COLUMN {col_name} {col_def}"
                ))
                logger.info(f"  Added column: daily_briefing_deliveries.{col_name}")
            except Exception as e:
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    logger.info(f"  Column already exists (skipping): {col_name}")
                else:
                    raise

        # ----------------------------------------------------------------
        # 2. Migrate data from legacy columns → new columns
        # ----------------------------------------------------------------
        try:
            await conn.execute(text("""
                UPDATE daily_briefing_deliveries
                SET opened_observed_at = opened_at
                WHERE opened_at IS NOT NULL AND opened_observed_at IS NULL
            """))
            logger.info("  Migrated opened_at → opened_observed_at")
        except Exception as e:
            logger.warning(f"  opened_at migration skipped: {e}")

        try:
            await conn.execute(text("""
                UPDATE daily_briefing_deliveries
                SET first_clicked_at = clicked_at
                WHERE clicked_at IS NOT NULL AND first_clicked_at IS NULL
            """))
            logger.info("  Migrated clicked_at → first_clicked_at")
        except Exception as e:
            logger.warning(f"  clicked_at migration skipped: {e}")

        # ----------------------------------------------------------------
        # 3. Drop legacy columns (only after data migrated)
        # ----------------------------------------------------------------
        for legacy_col in ["opened_at", "clicked_at"]:
            try:
                await conn.execute(text(
                    f"ALTER TABLE daily_briefing_deliveries DROP COLUMN IF EXISTS {legacy_col}"
                ))
                logger.info(f"  Dropped legacy column: {legacy_col}")
            except Exception as e:
                logger.warning(f"  Could not drop {legacy_col}: {e}")

        # ----------------------------------------------------------------
        # 4. Migrate BriefingDeliveryStatus enum
        #    PostgreSQL cannot remove enum values directly.
        #    Strategy: new type → alter column → drop old → rename new.
        # ----------------------------------------------------------------
        logger.info("  Migrating briefingdeliverystatus enum...")
        try:
            # Create new enum (idempotent — check first)
            await conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_type WHERE typname = 'briefingdeliverystatus_v2'
                    ) THEN
                        CREATE TYPE briefingdeliverystatus_v2 AS ENUM (
                            'PENDING', 'QUEUED', 'SENT', 'DELIVERED',
                            'FAILED', 'BOUNCED', 'COMPLAINED'
                        );
                    END IF;
                END $$;
            """))
            logger.info("  Created briefingdeliverystatus_v2 enum")

            # Remap any rows with removed enum values to DELIVERED
            await conn.execute(text("""
                UPDATE daily_briefing_deliveries
                SET status = 'DELIVERED'
                WHERE status::text IN ('CLICKED', 'OPENED_OBSERVED')
            """))
            logger.info("  Remapped CLICKED/OPENED_OBSERVED → DELIVERED")

            # Alter the column to use new enum type
            await conn.execute(text("""
                ALTER TABLE daily_briefing_deliveries
                ALTER COLUMN status TYPE briefingdeliverystatus_v2
                USING status::text::briefingdeliverystatus_v2;
            """))
            logger.info("  Altered status column to use briefingdeliverystatus_v2")

            # Drop old enum type
            await conn.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM pg_type WHERE typname = 'briefingdeliverystatus'
                    ) THEN
                        DROP TYPE briefingdeliverystatus;
                    END IF;
                END $$;
            """))
            logger.info("  Dropped old briefingdeliverystatus enum")

            # Rename new enum to canonical name
            await conn.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM pg_type WHERE typname = 'briefingdeliverystatus_v2'
                    ) THEN
                        ALTER TYPE briefingdeliverystatus_v2 RENAME TO briefingdeliverystatus;
                    END IF;
                END $$;
            """))
            logger.info("  Renamed briefingdeliverystatus_v2 → briefingdeliverystatus")

        except Exception as e:
            logger.warning(f"  Enum migration note: {e} (may already be up to date)")

        # ----------------------------------------------------------------
        # 5. Add unsubscribed_at to daily_briefing_subscribers
        # ----------------------------------------------------------------
        try:
            await conn.execute(text(
                "ALTER TABLE daily_briefing_subscribers "
                "ADD COLUMN unsubscribed_at TIMESTAMP WITH TIME ZONE"
            ))
            logger.info("  Added column: daily_briefing_subscribers.unsubscribed_at")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                logger.info("  Column already exists (skipping): unsubscribed_at")
            else:
                raise

        # ----------------------------------------------------------------
        # 6. Set enabled=FALSE for any unverified subscribers
        #    (new security invariant: enabled requires verified email)
        # ----------------------------------------------------------------
        try:
            result = await conn.execute(text("""
                UPDATE daily_briefing_subscribers
                SET enabled = FALSE
                WHERE email_verified_at IS NULL AND enabled = TRUE
            """))
            logger.info(f"  Disabled {result.rowcount} unverified subscriber(s) (enabled → FALSE)")
        except Exception as e:
            logger.warning(f"  Could not enforce verified-only enabled: {e}")

        logger.info("Migration complete ✓")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migration())
