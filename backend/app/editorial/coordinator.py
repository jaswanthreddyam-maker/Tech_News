import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.article import ProcessedArticle

logger = logging.getLogger("tech_news.editorial.coordinator")

REQUIRED_STAGES = {"thumbnail", "knowledge"}


class ArticleEnrichmentCoordinator:
    @staticmethod
    async def mark_stage_complete(db: AsyncSession, article_id: int, stage_name: str) -> None:
        """
        Marks a specific enrichment stage as complete for the given article.
        Once all REQUIRED_STAGES are complete, transitions the status,
        runs the scoring engine, and triggers the CQRS read model update event.
        """
        stmt = (
            select(ProcessedArticle)
            .options(selectinload(ProcessedArticle.category), selectinload(ProcessedArticle.source_ref))
            .where(ProcessedArticle.id == article_id)
        )
        res = await db.execute(stmt)
        art = res.scalars().first()

        if not art:
            logger.warning(f"Coordinator: ProcessedArticle {article_id} not found for stage '{stage_name}' update.")
            return

        # Initialize completed list as a set to avoid duplicates and ensure order-independent membership
        stages_set = set(art.completed_enrichment_stages or [])
        if stage_name not in stages_set:
            stages_set.add(stage_name)
            # Store as sorted list to guarantee deterministic database representation
            art.completed_enrichment_stages = sorted(list(stages_set))
            await db.flush()

        completed_set = stages_set

        if REQUIRED_STAGES.issubset(completed_set):
            # Only run scoring if not already calculated
            if art.final_score > 0.0:
                logger.info(f"Coordinator: Article {article_id} already has final_score={art.final_score}. Skipping.")
                return

            art.enrichment_status = "completed"

            # 1. Fetch extracted entities from database
            from app.models.tnt_knowledge import ArticleEntityLink, EntityNode

            entity_stmt = (
                select(EntityNode.canonical_name)
                .join(ArticleEntityLink, EntityNode.id == ArticleEntityLink.entity_id)
                .where(ArticleEntityLink.article_id == str(article_id))
            )
            entity_res = await db.execute(entity_stmt)
            entities = entity_res.scalars().all()

            # 2. Calculate impact score
            from app.editorial.policy import PolicyLoader
            from app.editorial.scoring import calculate_impact_score

            policy = PolicyLoader.get_policy()
            algo_ver = policy.get("algorithm_version", "v1")
            policy_ver = policy.get("policy_version", "unknown")

            impact = calculate_impact_score(art, entities)
            art.final_score = impact
            art.editorial_version = f"{algo_ver}:{policy_ver}"

            # 3. Emit Domain Event via Outbox
            from app.core.events.models import EventOutbox

            outbox_event = EventOutbox(
                event_type="ArticleImpactScoreUpdated",
                payload={
                    "article_id": str(article_id),
                    "impact_score": float(impact),
                    "editorial_version": art.editorial_version,
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            db.add(outbox_event)
            logger.info(
                f"Coordinator: All stages complete for article {article_id}. "
                f"Calculated impact_score={impact}, version={art.editorial_version}. Emitted ArticleImpactScoreUpdated event."
            )
        else:
            logger.info(
                f"Coordinator: Article {article_id} marked stage '{stage_name}' complete. "
                f"Remaining stages: {REQUIRED_STAGES - completed_set}"
            )


DefinitionName = "ArticleEnrichmentCoordinator"
