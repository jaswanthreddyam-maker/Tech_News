import logging

from celery import shared_task

from app.ai.summary_generator import SummaryGenerator
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

@shared_task(name="generate_structured_summary_task")
def generate_structured_summary_task(article_id: int):
    """
    Asynchronous Celery task to generate a structured AI summary.
    Invoked during article ingestion pipeline.
    """
    from celery_app import get_celery_session

    async def _run():
        async with get_celery_session() as session:
            try:
                generator = SummaryGenerator()
                summary = await generator.generate(session, article_id)

                # Update the database models: ProcessedArticle and ArticleReadModel
                from app.models.article import ProcessedArticle, ArticleReadModel
                from sqlalchemy import update

                takeaways_list = [t.model_dump() for t in summary.key_takeaways] if summary.key_takeaways else []

                # 1. Update ProcessedArticle
                stmt_proc = (
                    update(ProcessedArticle)
                    .where(ProcessedArticle.id == article_id)
                    .values(key_takeaways=takeaways_list)
                )
                await session.execute(stmt_proc)

                # 2. Update ArticleReadModel
                stmt_read = (
                    update(ArticleReadModel)
                    .where(ArticleReadModel.id == str(article_id))
                    .values(key_takeaways=takeaways_list)
                )
                await session.execute(stmt_read)
                await session.commit()

                # Cache the summary
                redis = get_redis_client()
                cache_key = f"ai_summary:article:{article_id}"
                await redis.set(cache_key, summary.model_dump_json(), ex=86400)

                # Invalidate homepage ranked IDs cache to ensure ordering reflects new metrics
                await redis.delete("editorial:v1:homepage_ranked_ids")

                logger.info(f"Successfully generated structured summary and takeaways for article {article_id}")
            except Exception as e:
                logger.error(f"Failed to generate structured summary for article {article_id}: {e}")

    # Run the async code in a synchronous wrapper
    from celery_app import run_in_worker_loop
    run_in_worker_loop(_run())
