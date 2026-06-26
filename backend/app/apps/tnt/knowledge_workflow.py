import asyncio
import logging
from typing import Any

from app.core.capability.knowledge import (
    EntityExtractionCapability,
    RelationshipExtractionCapability,
    TimelineExtractionCapability,
    TopicClassificationCapability,
)
from app.schemas.knowledge import KnowledgeArtifact

logger = logging.getLogger(__name__)

class KnowledgeWorkflow:
    """
    Deterministic orchestrator for Knowledge Extraction.
    Takes an ArticleArtifact as input, fans out to extraction capabilities,
    merges the results, and produces a KnowledgeArtifact.
    """
    def __init__(self):
        self.entity_cap = EntityExtractionCapability()
        self.topic_cap = TopicClassificationCapability()
        self.timeline_cap = TimelineExtractionCapability()
        self.relationship_cap = RelationshipExtractionCapability()

    async def execute(self, article: dict[str, Any]) -> KnowledgeArtifact:
        logger.info(f"Starting KnowledgeWorkflow for article {article.get('id')}")

        # 1. Fan Out
        # We run Entity, Topic, Timeline, and Relationship extractions in parallel.
        entity_task = self.entity_cap.execute({"article": article}, None)
        topic_task = self.topic_cap.execute({"article": article}, None)
        timeline_task = self.timeline_cap.execute({"article": article}, None)
        relationship_task = self.relationship_cap.execute({"article": article}, None)

        # Wait for all extractions to complete in parallel
        results = await asyncio.gather(
            entity_task,
            topic_task,
            timeline_task,
            relationship_task,
            return_exceptions=True
        )

        # Handle potential exceptions from parallel execution
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Extraction failed: {res}")
                # Depending on resilience strategy, we might fail the whole workflow
                # or proceed with partial results. We'll fail for strictness.
                raise res

        entity_result, topic_result, timeline_result, relationship_result = results

        # 2. Validation & Merge
        # (In a real system we'd validate dangling relationships, enforce canoncial entity IDs, etc.)
        merged_entities = entity_result.get("entities", [])
        merged_topics = topic_result.get("topics", [])
        merged_events = timeline_result.get("events", [])
        merged_relationships = relationship_result.get("relationships", [])

        # 3. Publish Knowledge Artifact
        knowledge_artifact = KnowledgeArtifact(
            artifact_id=article.get("id"),
            entities=merged_entities,
            topics=merged_topics,
            timeline=merged_events,
            relationships=merged_relationships
        )

        logger.info(f"KnowledgeWorkflow completed for {article.get('id')}")
        return knowledge_artifact
