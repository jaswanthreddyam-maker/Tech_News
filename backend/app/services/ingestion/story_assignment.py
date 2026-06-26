import logging
from typing import Optional, Tuple
from datetime import datetime, timezone
import uuid

from sqlalchemy import select, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.article import ProcessedArticle
from app.models.story import Story, StoryStatus, StoryAssignmentDecision

logger = logging.getLogger(__name__)

class StoryAssignmentEngine:
    THRESHOLD_AUTO_ASSIGN = 0.90
    THRESHOLD_EDITOR_REVIEW = 0.80
    MODEL_VERSION = "text-embedding-3-small" # Currently used model version for vectors

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate_article(self, article: ProcessedArticle) -> Tuple[str, Optional[str]]:
        """
        Evaluates an article's embedding against existing ACTIVE and DORMANT stories.
        Returns a tuple: (decision, candidate_story_id)
        """
        if article.embedding is None:
            logger.warning(f"Article {article.id} has no embedding. Defaulting to NEW_STORY.")
            await self._record_decision(str(article.id), None, None, self.THRESHOLD_AUTO_ASSIGN, "NEW_STORY")
            return "NEW_STORY", None

        # Fetch articles from ACTIVE or DORMANT stories, ideally we'd just query by max similarity using pgvector.
        # pgvector operator <-> is L2 distance, <=> is cosine distance, <#> is inner product.
        # Cosine similarity = 1 - cosine distance
        
        # We find the single closest article belonging to an active/dormant story.
        # ProcessedArticle.embedding.cosine_distance(article.embedding)
        
        stmt = (
            select(ProcessedArticle.story_id, ProcessedArticle.embedding.cosine_distance(article.embedding).label("distance"))
            .join(Story, Story.id == ProcessedArticle.story_id)
            .where(
                and_(
                    Story.status.in_([StoryStatus.ACTIVE, StoryStatus.DORMANT]),
                    ProcessedArticle.id != article.id,
                    ProcessedArticle.embedding.is_not(None)
                )
            )
            .order_by("distance")
            .limit(1)
        )
        
        result = await self.db.execute(stmt)
        row = result.first()
        
        if not row:
            await self._record_decision(str(article.id), None, None, self.THRESHOLD_AUTO_ASSIGN, "NEW_STORY")
            return "NEW_STORY", None
            
        candidate_story_id, distance = row
        similarity = 1.0 - float(distance)
        
        decision = "NEW_STORY"
        if similarity >= self.THRESHOLD_AUTO_ASSIGN:
            decision = "AUTO_ASSIGN"
        elif similarity >= self.THRESHOLD_EDITOR_REVIEW:
            decision = "EDITOR_REVIEW"
            
        await self._record_decision(str(article.id), candidate_story_id, similarity, self.THRESHOLD_AUTO_ASSIGN, decision)
        
        # Increment metric
        from app.core.metrics.ingestion import ingestion_metrics
        ingestion_metrics.story_assignment_decisions_total.labels(decision=decision).inc()
        
        if candidate_story_id:
            # Check if story is DORMANT
            story_status = await self.db.scalar(select(Story.status).where(Story.id == candidate_story_id))
            if story_status == StoryStatus.DORMANT:
                from app.core.events.models import EventOutbox
                if decision == "AUTO_ASSIGN":
                    # Emit Reawakened
                    payload = {"story_id": candidate_story_id, "article_id": str(article.id), "similarity": similarity}
                    self.db.add(EventOutbox(event_type="StoryReawakened", payload=payload))
                    # Optionally transition back to active (the processor or this service can do it)
                    await self.db.execute(update(Story).where(Story.id == candidate_story_id).values(status=StoryStatus.ACTIVE))
                elif decision == "EDITOR_REVIEW":
                    # Emit FollowUpSuggested
                    payload = {"story_id": candidate_story_id, "article_id": str(article.id), "similarity": similarity}
                    self.db.add(EventOutbox(event_type="FollowUpSuggested", payload=payload))
                await self.db.flush()
                
        return decision, candidate_story_id

    async def _record_decision(self, article_id: str, candidate_story_id: Optional[str], similarity: Optional[float], threshold: float, decision: str):
        decision_log = StoryAssignmentDecision(
            article_id=article_id,
            candidate_story_id=candidate_story_id,
            similarity_score=similarity,
            threshold_used=threshold,
            decision=decision,
            model_version=self.MODEL_VERSION
        )
        self.db.add(decision_log)
        await self.db.flush()
        logger.info(f"Recorded assignment decision: {decision} for article {article_id}. Sim: {similarity}")

