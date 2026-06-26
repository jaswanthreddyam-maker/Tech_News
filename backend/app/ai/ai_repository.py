import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import AITelemetryRecord
from app.models.user import AIJobHistory

logger = logging.getLogger("tech_news.ai_repository")


async def persist_telemetry(
    db: AsyncSession,
    raw_article_id: int | None,
    processed_article_id: int | None,
    records: list[AITelemetryRecord],
) -> list[int]:
    """
    Bulk-inserts one AIJobHistory row per AITelemetryRecord (task_type).
    Returns the list of inserted AIJobHistory IDs.
    """
    inserted_ids = []
    for record in records:
        try:
            job_history = AIJobHistory(
                raw_article_id=raw_article_id,
                processed_article_id=processed_article_id,
                provider=record.provider,
                task_type=record.task_type,
                model=record.model,
                prompt_version=record.prompt_version,
                prompt_hash=record.prompt_hash,
                prompt_tokens=record.prompt_tokens,
                completion_tokens=record.completion_tokens,
                total_tokens=record.total_tokens,
                cost_usd=record.cost_usd,
                cache_hit=record.cache_hit,
                retry_count=record.retry_count,
                provider_metadata=record.provider_metadata,
                enrichment_input_fingerprint=record.enrichment_input_fingerprint,
                status=record.status.value if hasattr(record.status, "value") else record.status,
                error=record.error,
                started_at=record.started_at,
                finished_at=record.finished_at,
                created_at=datetime.now(timezone.utc),
            )
            db.add(job_history)
            await db.flush()  # Flush to get the ID
            inserted_ids.append(job_history.id)
        except Exception as e:
            logger.error(f"Failed to persist telemetry record for task {record.task_type}: {e}", exc_info=True)
            raise  # Let the enclosing transaction handle rollback

    return inserted_ids
