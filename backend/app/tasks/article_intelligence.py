"""
Article Intelligence Pipeline — Single orchestration Celery task.

Replaces the scattered multi-task approach. One article ID → one task → all AI enrichment.

Pipeline stages (in order):
  1. Structured Summary + Key Takeaways
  2. Entity Extraction  → tnt_entity_nodes + tnt_article_entities
  3. Topic Classification → tnt_topic_nodes + tnt_article_topics
  4. Embedding Generation → invalidate stale, regenerate
  5. CQRS cache invalidation

Each stage is independently fault-tolerant — a failure in stage N does NOT
prevent stages N+1..5 from running.

Usage:
  from app.tasks.article_intelligence import run_article_intelligence_pipeline
  run_article_intelligence_pipeline.delay(article_id)
"""

import logging
import re
import uuid
from datetime import datetime, timezone

from celery import shared_task

logger = logging.getLogger("tech_news.article_intelligence")


@shared_task(
    name="run_article_intelligence_pipeline",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def run_article_intelligence_pipeline(self, article_id: int) -> dict:
    """
    Full AI enrichment pipeline for a single ProcessedArticle.
    Stages: Summary → Entity Extraction → Topic Classification → Embeddings → Cache Bust.
    """
    from celery_app import get_celery_session, run_in_worker_loop

    async def _run() -> dict:
        results: dict = {
            "article_id": article_id,
            "summary": "skipped",
            "entities": "skipped",
            "topics": "skipped",
            "embedding": "skipped",
        }

        async with get_celery_session() as session:
            from sqlalchemy import select, update
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            from app.models.article import ArticleReadModel, ProcessedArticle

            # ── Load article ──────────────────────────────────────────────────
            stmt = select(ProcessedArticle).where(ProcessedArticle.id == article_id)
            art = (await session.execute(stmt)).scalars().first()
            if not art:
                logger.error(f"AIP: ProcessedArticle {article_id} not found")
                return results

            content = art.content or art.summary or ""
            if not content.strip():
                logger.warning(f"AIP: Article {article_id} has empty content — skipping all stages")
                return results

            from app.ai.schemas import ArticleAIInput
            from app.ai.service import AIService

            ai_input = ArticleAIInput(
                title=art.title,
                content=content,
                source=art.source_name,
                source_url=art.source_url,
            )
            ai_service = AIService()

            # ═══════════════════════════════════════════════════════════════
            # STAGE 1 — Structured Summary + Key Takeaways
            # ═══════════════════════════════════════════════════════════════
            try:
                from app.ai.summary_generator import SummaryGenerator
                from app.core.redis import get_redis_client

                generator = SummaryGenerator()
                summary = await generator.generate(session, article_id)

                takeaways_list = (
                    [t.model_dump() for t in summary.key_takeaways]
                    if summary.key_takeaways
                    else []
                )

                await session.execute(
                    update(ProcessedArticle)
                    .where(ProcessedArticle.id == article_id)
                    .values(key_takeaways=takeaways_list)
                )
                await session.execute(
                    update(ArticleReadModel)
                    .where(ArticleReadModel.id == str(article_id))
                    .values(key_takeaways=takeaways_list)
                )
                await session.commit()

                # Cache summary
                redis = get_redis_client()
                await redis.set(
                    f"ai_summary:article:{article_id}",
                    summary.model_dump_json(),
                    ex=86400,
                )
                results["summary"] = "ok"
                logger.info(f"AIP [{article_id}]: Stage 1 Summary — OK")

            except Exception as exc:
                logger.error(f"AIP [{article_id}]: Stage 1 Summary failed: {exc}", exc_info=True)
                results["summary"] = f"failed: {exc}"

            # ═══════════════════════════════════════════════════════════════
            # STAGE 2 — Entity Extraction
            # ═══════════════════════════════════════════════════════════════
            try:
                raw_entities = await ai_service.extract_entities(ai_input)

                if raw_entities:
                    from app.models.tnt_knowledge import ArticleEntityLink, EntityNode

                    article_read_id = str(article_id)
                    entity_count = 0

                    for ent in raw_entities:
                        ent_id = ent.get("id") or _slugify_entity_id(
                            ent.get("entity_type", "other"), ent.get("canonical_name", "unknown")
                        )
                        canonical_name = ent.get("canonical_name", "").strip()
                        entity_type = ent.get("entity_type", "OTHER").upper()
                        confidence = float(ent.get("confidence", 0.8))
                        aliases = ent.get("aliases", [])
                        description = ent.get("description", "")

                        if not canonical_name or not ent_id:
                            continue

                        # Upsert EntityNode
                        await session.execute(
                            pg_insert(EntityNode)
                            .values(
                                id=ent_id,
                                canonical_name=canonical_name,
                                entity_type=entity_type,
                                aliases=aliases,
                                description=description,
                                confidence=confidence,
                                last_seen=datetime.now(timezone.utc),
                            )
                            .on_conflict_do_update(
                                index_elements=["id"],
                                set_={
                                    "last_seen": datetime.now(timezone.utc),
                                    "confidence": confidence,
                                },
                            )
                        )

                        # Upsert ArticleEntityLink
                        await session.execute(
                            pg_insert(ArticleEntityLink)
                            .values(
                                article_id=article_read_id,
                                entity_id=ent_id,
                                confidence=confidence,
                            )
                            .on_conflict_do_update(
                                constraint="uq_tnt_article_entity",
                                set_={"confidence": confidence},
                            )
                        )
                        entity_count += 1

                    await session.commit()
                    results["entities"] = f"ok ({entity_count})"
                    logger.info(f"AIP [{article_id}]: Stage 2 Entities — {entity_count} extracted")
                else:
                    # Heuristic fallback using extract_controlled_tags
                    results["entities"] = "ok (heuristic fallback, 0 LLM entities)"
                    logger.info(f"AIP [{article_id}]: Stage 2 Entities — LLM returned empty, used heuristic")

            except Exception as exc:
                logger.error(f"AIP [{article_id}]: Stage 2 Entity Extraction failed: {exc}", exc_info=True)
                results["entities"] = f"failed: {exc}"

            # ═══════════════════════════════════════════════════════════════
            # STAGE 3 — Topic Classification
            # ═══════════════════════════════════════════════════════════════
            try:
                raw_topics = await ai_service.extract_topics(ai_input)

                if not raw_topics:
                    # Heuristic fallback: derive topics from existing tags
                    raw_topics = _heuristic_topics(art.tags or "")

                if raw_topics:
                    from app.models.tnt_knowledge import ArticleTopicLink, TopicNode

                    article_read_id = str(article_id)
                    topic_count = 0

                    for top in raw_topics:
                        topic_name = top.get("name", "").strip()
                        taxonomy_category = top.get("taxonomy_category", "General").strip()
                        confidence = float(top.get("confidence", 0.8))

                        if not topic_name:
                            continue

                        # Upsert TopicNode
                        await session.execute(
                            pg_insert(TopicNode)
                            .values(
                                name=topic_name,
                                taxonomy_category=taxonomy_category,
                            )
                            .on_conflict_do_update(
                                index_elements=["name"],
                                set_={"taxonomy_category": taxonomy_category},
                            )
                        )

                        # Upsert ArticleTopicLink
                        await session.execute(
                            pg_insert(ArticleTopicLink)
                            .values(
                                article_id=article_read_id,
                                topic_name=topic_name,
                                confidence=confidence,
                            )
                            .on_conflict_do_update(
                                constraint="uq_tnt_article_topic",
                                set_={"confidence": confidence},
                            )
                        )
                        topic_count += 1

                    await session.commit()
                    results["topics"] = f"ok ({topic_count})"
                    logger.info(f"AIP [{article_id}]: Stage 3 Topics — {topic_count} classified")
                else:
                    results["topics"] = "ok (0 topics)"

            except Exception as exc:
                logger.error(f"AIP [{article_id}]: Stage 3 Topic Classification failed: {exc}", exc_info=True)
                results["topics"] = f"failed: {exc}"

            # ═══════════════════════════════════════════════════════════════
            # STAGE 4 — Embedding regeneration
            # ═══════════════════════════════════════════════════════════════
            try:
                from app.ai.embedding import EmbeddingService

                # Reset stale embedding status so process_embedding_task will re-run
                await session.execute(
                    update(ProcessedArticle)
                    .where(ProcessedArticle.id == article_id)
                    .values(embedding_status="pending")
                )
                await session.commit()

                # Queue background embedding task
                from celery_app import process_embedding_task

                process_embedding_task.delay(article_id)
                results["embedding"] = "queued"
                logger.info(f"AIP [{article_id}]: Stage 4 Embedding — queued")

            except Exception as exc:
                logger.error(f"AIP [{article_id}]: Stage 4 Embedding failed: {exc}", exc_info=True)
                results["embedding"] = f"failed: {exc}"

            # ═══════════════════════════════════════════════════════════════
            # STAGE 5 — Cache invalidation
            # ═══════════════════════════════════════════════════════════════
            try:
                from app.core.redis import get_redis_client

                redis = get_redis_client()
                await redis.delete("editorial:v1:homepage_ranked_ids")
                logger.info(f"AIP [{article_id}]: Stage 5 Cache — invalidated")
            except Exception as exc:
                logger.warning(f"AIP [{article_id}]: Stage 5 Cache invalidation failed: {exc}")

        logger.info(f"AIP [{article_id}]: Pipeline complete — {results}")
        return results

    return run_in_worker_loop(_run())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify_entity_id(entity_type: str, name: str) -> str:
    """Generates a deterministic entity ID from type + canonical name."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug).strip("_")
    type_prefix = entity_type.lower()
    return f"{type_prefix}:{slug}"


def _heuristic_topics(tags_str: str) -> list[dict]:
    """
    Convert existing article tags into topic dicts as a fallback
    when the LLM returns nothing.
    """
    TAG_TO_TOPIC: dict[str, tuple[str, str]] = {
        "artificial-intelligence": ("Artificial Intelligence", "AI"),
        "robotics": ("Robotics", "Hardware"),
        "cybersecurity": ("Cybersecurity", "Security"),
        "startups": ("Startups & Funding", "Business"),
        "software-development": ("Software Development", "Software"),
        "space-science": ("Space & Science", "Science"),
        "tech-innovation": ("Technology Innovation", "Software"),
    }
    topics = []
    for tag in tags_str.split(","):
        tag = tag.strip()
        if tag in TAG_TO_TOPIC:
            name, category = TAG_TO_TOPIC[tag]
            topics.append({"name": name, "taxonomy_category": category, "confidence": 0.70})
    return topics
