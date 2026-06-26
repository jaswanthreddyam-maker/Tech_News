import argparse
import asyncio
import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle
from celery_app import process_embedding_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tech_news.cli.embedding")


async def backfill(missing: bool, stale: bool, all_: bool, batch_size: int, dry_run: bool):
    """Backfill missing or stale embeddings using celery tasks."""
    async with AsyncSessionLocal() as session:
        conditions = []
        if missing:
            conditions.append(ProcessedArticle.embedding_status.in_(["pending", "failed"]))
            conditions.append(ProcessedArticle.embedding_status.is_(None))
        if stale:
            conditions.append(ProcessedArticle.embedding_status == "stale")

        stmt = select(ProcessedArticle.id)
        if not all_:
            from sqlalchemy import or_

            stmt = stmt.where(or_(*conditions))

        stmt = stmt.limit(batch_size)

        result = await session.execute(stmt)
        article_ids = result.scalars().all()

        if not article_ids:
            logger.info("No articles found requiring embedding generation.")
            return

        logger.info(f"Found {len(article_ids)} articles requiring embedding generation.")

        if dry_run:
            logger.info("Dry run enabled. No tasks enqueued.")
            return

        for article_id in article_ids:
            # Optionally update state to 'queued' immediately here
            # But the task will handle its own states if designed well,
            # For correctness, we can update it to queued here
            stmt_update = select(ProcessedArticle).where(ProcessedArticle.id == article_id)
            article = (await session.execute(stmt_update)).scalar_one_or_none()
            if article:
                article.embedding_status = "queued"

            process_embedding_task.delay(article_id)

        await session.commit()
        logger.info(f"Successfully enqueued {len(article_ids)} embedding tasks.")


def main():
    parser = argparse.ArgumentParser(description="Manage Semantic Search Embeddings")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backfill_parser = subparsers.add_parser("backfill", help="Backfill missing/stale embeddings")
    backfill_parser.add_argument(
        "--missing", action="store_true", help="Backfill articles with missing or failed embeddings"
    )
    backfill_parser.add_argument("--stale", action="store_true", help="Backfill articles with stale embeddings")
    backfill_parser.add_argument("--all", action="store_true", help="Backfill all articles (forces re-embedding)")
    backfill_parser.add_argument("--batch-size", type=int, default=100, help="Maximum number of articles to backfill")
    backfill_parser.add_argument(
        "--dry-run", action="store_true", help="Print what would happen without enqueueing tasks"
    )

    args = parser.parse_args()

    if args.command == "backfill":
        if not any([args.missing, args.stale, args.all]):
            parser.error("Must specify one of --missing, --stale, or --all")

        asyncio.run(
            backfill(
                missing=args.missing, stale=args.stale, all_=args.all, batch_size=args.batch_size, dry_run=args.dry_run
            )
        )


if __name__ == "__main__":
    main()
