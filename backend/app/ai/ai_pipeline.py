import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.config import AIConfig
from app.ai.fingerprint import build_enrichment_input_fingerprint
from app.ai.schemas import AIJobStatus, AIServiceResult, AITaskType, ArticleAIInput
from app.ai.service import AIService
from app.core.config import settings
from app.models.article import RawArticle
from app.models.growth import FeatureFlag

logger = logging.getLogger("tech_news.ai_pipeline")


async def enrich_raw_article(db: AsyncSession, raw_id: int) -> AIServiceResult | None:
    """
    Attempts to enrich a raw article using the AI infrastructure.
    Returns None if AI enrichment is disabled via FeatureFlag or AI_PROVIDER config.
    Returns AIServiceResult (COMPLETED or FALLBACK) if enrichment was attempted.
    """
    # 1. Check if AI enrichment is explicitly disabled in config
    if settings.AI_PROVIDER == "disabled":
        logger.info(f"AI Pipeline: Skipping enrichment for RawArticle {raw_id} (AI_PROVIDER=disabled)")
        return None

    # 2. Check FeatureFlag("ai_enrichment_enabled") at runtime
    flag_stmt = select(FeatureFlag).where(FeatureFlag.key == "ai_enrichment_enabled")
    flag_res = await db.execute(flag_stmt)
    feature_flag = flag_res.scalars().first()

    is_enabled = False
    if feature_flag:
        val = feature_flag.default_value
        if isinstance(val, dict):
            is_enabled = val.get("enabled", False)
        else:
            is_enabled = bool(val)

    if not is_enabled:
        from app.core.event_bus import publish_event

        await publish_event("AI_PIPELINE", f"AI skipped for RawArticle {raw_id}: feature_flag_disabled", "info")
        logger.info(f"AI Pipeline: Skipping enrichment for RawArticle {raw_id} (ai_enrichment_enabled=False)")
        return None

    # 3. Load RawArticle
    stmt = select(RawArticle).where(RawArticle.id == raw_id)
    res = await db.execute(stmt)
    raw_article = res.scalars().first()

    if not raw_article:
        logger.error(f"AI Pipeline: RawArticle ID {raw_id} not found.")
        return None

    # Extract clean text for processing
    content = raw_article.clean_text or raw_article.title or "No article content available."

    # Heuristic Fallback Generation
    # Create the baseline heuristic summary as fallback
    import re

    from app.services.ingestion.processor import extract_controlled_tags

    sentences = re.split(r"(?<=[.!?])\s+", content)
    heuristic_summary = " ".join(sentences[:2])
    if len(heuristic_summary) > 280:
        heuristic_summary = heuristic_summary[:277] + "..."
    if not heuristic_summary:
        heuristic_summary = "No summary compiled yet."

    heuristic_tags = extract_controlled_tags(raw_article.title, content)

    # 4. Build ArticleAIInput
    article_input = ArticleAIInput(
        title=raw_article.title,
        content=content,
        source=raw_article.source.name if raw_article.source else "System Ingest",
        source_url=raw_article.url,
    )

    # 5. Call AIService
    ai_service = AIService()
    try:
        from app.ai.schemas import AIEnrichmentOutput, SentimentLabel

        fallback_output = AIEnrichmentOutput(
            summary=heuristic_summary,
            keywords=[],
            tags=heuristic_tags.split(",") if heuristic_tags else [],
            sentiment=SentimentLabel.NEUTRAL,
        )

        logger.info(f"AI Pipeline: Initiating enrichment for '{raw_article.title}'")
        result = await ai_service.enrich_article(article=article_input, fallback=fallback_output)
        return result
    except Exception as e:
        logger.error(f"AI Pipeline: Unhandled exception during enrichment for RawArticle {raw_id}: {e}", exc_info=True)
        # Should not happen as AIService catches its own exceptions, but safety net
        # Construct a fallback result manually
        from datetime import datetime, timezone

        from app.ai.schemas import AIEnrichmentOutput, AITelemetryRecord, SentimentLabel

        ai_config = AIConfig()
        prompt_version = ai_config.prompt_version_for(AITaskType.SUMMARY)
        clipped_content = article_input.content[: ai_config.max_input_chars]
        provider_metadata = {
            "provider": ai_config.provider,
            "model": ai_config.summary_model,
            "prompt_version": prompt_version,
            "sdk_version": None,
            "response_format": None,
        }
        enrichment_input_fingerprint = build_enrichment_input_fingerprint(
            title=article_input.title,
            content=clipped_content,
            prompt_version=prompt_version,
            provider=ai_config.provider,
            model=ai_config.summary_model,
        )

        fallback_output = AIEnrichmentOutput(
            summary=heuristic_summary,
            keywords=[],
            tags=heuristic_tags.split(",") if heuristic_tags else [],
            sentiment=SentimentLabel.NEUTRAL,
        )

        telemetry = AITelemetryRecord(
            provider=ai_config.provider,
            task_type=AITaskType.SUMMARY,
            model=ai_config.summary_model,
            prompt_version=prompt_version,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cost_usd="0.000000",
            cache_hit=False,
            retry_count=0,
            status=AIJobStatus.FALLBACK,
            error=str(e),
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            provider_metadata=provider_metadata,
            enrichment_input_fingerprint=enrichment_input_fingerprint,
        )

        return AIServiceResult(status=AIJobStatus.FALLBACK, output=fallback_output, telemetry=[telemetry])
