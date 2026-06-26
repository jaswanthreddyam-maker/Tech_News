import logging
from datetime import datetime
from typing import Any

from dateutil import parser as date_parser
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ArticleReadModel
from app.models.story import StoryTimelineEvent, StoryMilestoneType
from app.models.tnt_knowledge import (
    ArticleEntityLink,
    ArticleTopicLink,
    EntityNode,
    RelationshipEdge,
    TimelineEventNode,
    TopicNode,
)
from app.schemas.knowledge import KnowledgeArtifact

logger = logging.getLogger(__name__)

class StoryProjector:
    """Projects events into the StoryTimelineReadModel."""
    async def handle_timeline_event(self, event_type: str, payload: dict[str, Any], event_id: int, session: AsyncSession) -> None:
        story_id = payload.get("story_id")
        if not story_id:
            logger.warning(f"No story_id in payload for event {event_type}, skipping timeline projection.")
            return
            
        # Idempotency check: Don't project the same outbox event twice
        stmt_check = select(StoryTimelineEvent.id).where(StoryTimelineEvent.source_event_id == event_id)
        res = await session.execute(stmt_check)
        if res.first():
            logger.info(f"Timeline event for outbox event {event_id} already projected. Skipping.")
            return

        article_id = payload.get("article_id")
        milestone = payload.get("milestone_type")
        
        milestone_type = None
        if milestone and hasattr(StoryMilestoneType, milestone):
            milestone_type = StoryMilestoneType[milestone]

        stmt = insert(StoryTimelineEvent).values(
            story_id=str(story_id),
            source_event_id=event_id,
            event_type=event_type,
            article_id=str(article_id) if article_id else None,
            milestone_type=milestone_type,
            payload=payload
        )
        await session.execute(stmt)
        
        # Maintain CQRS Dashboard Projection
        from app.models.story import StoryDashboardProjection
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        
        title = payload.get("title", "Untitled Narrative")
        status = payload.get("status", "ACTIVE")
        editorial_status = payload.get("editorial_status", "DRAFT")
        publication_status = payload.get("publication_status", "DRAFT")
        
        now = datetime.now(timezone.utc) if 'timezone' in globals() else datetime.now()
        proj_stmt = pg_insert(StoryDashboardProjection).values(
            story_id=str(story_id),
            title=title,
            status=status,
            editorial_status=editorial_status,
            publication_status=publication_status,
            last_activity_at=now
        )
        proj_stmt = proj_stmt.on_conflict_do_update(
            index_elements=['story_id'],
            set_={
                'title': proj_stmt.excluded.title,
                'status': proj_stmt.excluded.status,
                'editorial_status': proj_stmt.excluded.editorial_status,
                'publication_status': proj_stmt.excluded.publication_status,
                'last_activity_at': proj_stmt.excluded.last_activity_at
            }
        )
        await session.execute(proj_stmt)
        
        await session.commit()
        logger.info(f"Successfully appended {event_type} to story timeline for {story_id} and updated projection.")
        
        # Publish Actionable Events to SSE Stream
        import json
        from app.core.redis import get_redis_client
        actionable_events = {"StoryReawakened", "CoverageGapDetected", "AssignmentReviewCreated", "ArticleApproved", "StoryAssignmentDecisionCreated"}
        if event_type in actionable_events:
            redis = get_redis_client()
            message = json.dumps({
                "type": event_type,
                "story_id": str(story_id),
                "article_id": str(article_id) if article_id else None,
                "timestamp": now.isoformat()
            })
            await redis.publish("editorial_events", message)
            logger.info(f"Published actionable event {event_type} to editorial_events channel.")

class ArticleProjector:
    """
    Listens to 'Published ArticleArtifact' events and projects the canonical data
    into the SQL 'articles' read model.
    """
    async def project(self, artifact_id: str, article_data: dict[str, Any], session: AsyncSession) -> None:
        logger.info(f"Projecting article {artifact_id} into read model.")

        # Parse dates
        pub_at = None
        if article_data.get("published_at"):
            try:
                pub_at = date_parser.parse(article_data["published_at"])
            except Exception:
                pass

        upd_at = None
        if article_data.get("updated_at"):
            try:
                upd_at = date_parser.parse(article_data["updated_at"])
            except Exception:
                pass

        stmt = insert(ArticleReadModel).values(
            id=artifact_id,
            url=article_data["url"],
            canonical_url=article_data.get("canonical_url"),
            title=article_data["title"],
            subtitle=article_data.get("subtitle"),
            author=article_data.get("author"),
            published_at=pub_at,
            updated_at=upd_at,
            language=article_data.get("language", "en"),
            summary=article_data.get("summary"),
            content=article_data["content"],
            word_count=article_data.get("word_count", 0),
            reading_time=article_data.get("reading_time", 0),
            images=article_data.get("images", []),
            tags=article_data.get("tags", []),
            source=article_data.get("source", "Web"),
            license=article_data.get("license"),
            hash=article_data["hash"],
            thumbnail_url=article_data.get("thumbnail_url"),
            thumbnail_local=article_data.get("thumbnail_local"),
            key_takeaways=article_data.get("key_takeaways"),
            is_test_data=article_data.get("is_test_data", False),
            freshness_score=article_data.get("freshness_score", 0.0),
            engagement_score=article_data.get("engagement_score", 0.0),
            final_score=article_data.get("final_score", 0.0),
            category=article_data.get("category"),
            published_status=article_data.get("published_status")
        )

        # Upsert logic (DO UPDATE SET) to keep projection perfectly synced
        stmt = stmt.on_conflict_do_update(
            index_elements=['url'], # unique constraint
            set_={
                'title': stmt.excluded.title,
                'subtitle': stmt.excluded.subtitle,
                'summary': stmt.excluded.summary,
                'content': stmt.excluded.content,
                'word_count': stmt.excluded.word_count,
                'reading_time': stmt.excluded.reading_time,
                'images': stmt.excluded.images,
                'tags': stmt.excluded.tags,
                'key_takeaways': stmt.excluded.key_takeaways,
                'hash': stmt.excluded.hash,
                'updated_at': stmt.excluded.updated_at,
                'published_at': stmt.excluded.published_at,
                'thumbnail_url': stmt.excluded.thumbnail_url,
                'thumbnail_local': stmt.excluded.thumbnail_local,
                'is_test_data': stmt.excluded.is_test_data,
                'freshness_score': stmt.excluded.freshness_score,
                'engagement_score': stmt.excluded.engagement_score,
                'final_score': stmt.excluded.final_score,
                'category': stmt.excluded.category,
                'published_status': stmt.excluded.published_status
            }
        )

        await session.execute(stmt)
        await session.commit()
        logger.info(f"Successfully projected article {artifact_id} to read model.")

    async def handle_thumbnail_updated(self, payload: dict[str, Any], session: AsyncSession) -> None:
        """
        Targeted projection handler for the ArticleThumbnailUpdated domain event.
        Updates only the thumbnail-related columns in the read model without overwriting other fields.
        """
        from sqlalchemy import update

        artifact_id = payload["article_id"]
        logger.info(f"Applying ArticleThumbnailUpdated to read model for {artifact_id}")

        stmt = (
            update(ArticleReadModel)
            .where(ArticleReadModel.id == artifact_id)
            .values(
                thumbnail_local=payload.get("thumbnail_local"),
                thumbnail_url=payload.get("thumbnail_url"),
                hash=payload.get("thumbnail_hash")
            )
        )

        res = await session.execute(stmt)
        if res.rowcount > 0:
            logger.info(f"Successfully updated thumbnail fields in read model for {artifact_id}.")
        else:
            logger.warning(f"Could not update thumbnail fields for {artifact_id} in read model (not found).")

        await session.commit()

    async def handle_impact_score_updated(self, payload: dict[str, Any], session: AsyncSession) -> None:
        """
        Targeted projection handler for the ArticleImpactScoreUpdated domain event.
        Updates only the final_score in the read model.
        """
        from sqlalchemy import update

        artifact_id = payload["article_id"]
        logger.info(f"Applying ArticleImpactScoreUpdated to read model for {artifact_id}")

        stmt = (
            update(ArticleReadModel)
            .where(ArticleReadModel.id == artifact_id)
            .values(
                final_score=payload.get("impact_score")
            )
        )

        res = await session.execute(stmt)
        if res.rowcount > 0:
            logger.info(f"Successfully updated impact_score field in read model for {artifact_id}.")
        else:
            logger.warning(f"Could not update impact_score field for {artifact_id} in read model (not found).")

        await session.commit()

    async def handle_lifecycle_updated(self, payload: dict[str, Any], session: AsyncSession) -> None:
        """
        Targeted projection handler for Editorial/Publication lifecycle events.
        """
        from sqlalchemy import update

        artifact_id = str(payload.get("article_id") or payload.get("id", ""))
        logger.info(f"Applying Lifecycle Update to read model for {artifact_id}")

        values_to_update = {}
        if "editorial_status" in payload:
            values_to_update["editorial_status"] = payload["editorial_status"]
        if "publication_status" in payload:
            values_to_update["publication_status"] = payload["publication_status"]
        if "scheduled_for" in payload:
            values_to_update["scheduled_for"] = date_parser.parse(payload["scheduled_for"]) if payload["scheduled_for"] else None
        if "published_at" in payload:
            values_to_update["published_at"] = date_parser.parse(payload["published_at"]) if payload["published_at"] else None

        if not values_to_update:
            return

        stmt = (
            update(ArticleReadModel)
            .where(ArticleReadModel.id == artifact_id)
            .values(**values_to_update)
        )

        res = await session.execute(stmt)
        if res.rowcount > 0:
            logger.info(f"Successfully updated lifecycle fields in read model for {artifact_id}.")
        else:
            logger.warning(f"Could not update lifecycle fields for {artifact_id} in read model (not found).")

        await session.commit()

    async def handle_stories_merged(self, payload: dict[str, Any], session: AsyncSession) -> None:
        """
        Targeted projection handler for StoriesMerged event.
        Updates the story_id of all read models from the source story to the target story.
        """
        from sqlalchemy import update
        target_id = payload.get("story_id")
        source_id = payload.get("source_story_id")
        
        if not target_id or not source_id:
            return

        stmt = (
            update(ArticleReadModel)
            .where(ArticleReadModel.story_id == source_id)
            .values(story_id=target_id)
        )
        res = await session.execute(stmt)
        logger.info(f"Successfully updated {res.rowcount} articles from story {source_id} to {target_id} in read model.")
        await session.commit()


class EntityProjector:
    async def project(self, artifact: KnowledgeArtifact, session: AsyncSession) -> None:
        if not artifact.entities:
            return

        # Delete existing links for replayability
        await session.execute(
            ArticleEntityLink.__table__.delete().where(ArticleEntityLink.article_id == artifact.artifact_id)
        )

        for ent in artifact.entities:
            # Upsert Entity Node
            stmt = insert(EntityNode).values(
                id=ent.id,
                canonical_name=ent.canonical_name,
                entity_type=ent.entity_type.value if hasattr(ent.entity_type, 'value') else ent.entity_type,
                aliases=ent.aliases,
                description=ent.description,
                confidence=ent.confidence
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=['id'],
                set_={
                    'canonical_name': stmt.excluded.canonical_name,
                    'aliases': stmt.excluded.aliases,
                    'description': stmt.excluded.description,
                    'confidence': stmt.excluded.confidence,
                    'last_seen': datetime.now()
                }
            )
            await session.execute(stmt)

            # Insert Link
            link_stmt = insert(ArticleEntityLink).values(
                article_id=artifact.artifact_id,
                entity_id=ent.id,
                confidence=ent.confidence
            )
            link_stmt = link_stmt.on_conflict_do_nothing(index_elements=['article_id', 'entity_id'])
            await session.execute(link_stmt)

        await session.commit()

class TopicProjector:
    async def project(self, artifact: KnowledgeArtifact, session: AsyncSession) -> None:
        if not artifact.topics:
            return

        await session.execute(
            ArticleTopicLink.__table__.delete().where(ArticleTopicLink.article_id == artifact.artifact_id)
        )

        for topic in artifact.topics:
            stmt = insert(TopicNode).values(
                name=topic.name,
                taxonomy_category=topic.taxonomy_category.value if hasattr(topic.taxonomy_category, 'value') else topic.taxonomy_category
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=['name'])
            await session.execute(stmt)

            link_stmt = insert(ArticleTopicLink).values(
                article_id=artifact.artifact_id,
                topic_name=topic.name,
                confidence=topic.confidence
            )
            link_stmt = link_stmt.on_conflict_do_nothing(index_elements=['article_id', 'topic_name'])
            await session.execute(link_stmt)

        await session.commit()

class TimelineProjector:
    async def project(self, artifact: KnowledgeArtifact, session: AsyncSession) -> None:
        # Delete existing
        await session.execute(
            TimelineEventNode.__table__.delete().where(TimelineEventNode.article_id == artifact.artifact_id)
        )

        if not artifact.timeline:
            return

        for event in artifact.timeline:
            stmt = insert(TimelineEventNode).values(
                article_id=artifact.artifact_id,
                event_type=event.event_type,
                date=event.date,
                certainty=event.certainty.value if hasattr(event.certainty, 'value') else event.certainty,
                entities=event.entities,
                description=event.description,
                confidence=event.confidence
            )
            await session.execute(stmt)

        await session.commit()

class RelationshipProjector:
    async def project(self, artifact: KnowledgeArtifact, session: AsyncSession) -> None:
        await session.execute(
            RelationshipEdge.__table__.delete().where(RelationshipEdge.article_id == artifact.artifact_id)
        )

        if not artifact.relationships:
            return

        for rel in artifact.relationships:
            # Ensure nodes exist (they should, due to EntityProjector, but just in case)
            stmt = insert(RelationshipEdge).values(
                article_id=artifact.artifact_id,
                source_id=rel.source,
                predicate=rel.predicate.value if hasattr(rel.predicate, 'value') else rel.predicate,
                target_id=rel.target,
                confidence=rel.confidence
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=['article_id', 'source_id', 'predicate', 'target_id'])
            await session.execute(stmt)

        await session.commit()

class KnowledgeGraphProjector:
    """Coordinator projector for all Knowledge Graph components."""
    def __init__(self):
        self.entity_projector = EntityProjector()
        self.topic_projector = TopicProjector()
        self.timeline_projector = TimelineProjector()
        self.relationship_projector = RelationshipProjector()

    async def project(self, artifact: KnowledgeArtifact, session: AsyncSession) -> None:
        logger.info(f"Projecting knowledge graph for artifact {artifact.artifact_id}")
        await self.entity_projector.project(artifact, session)
        await self.topic_projector.project(artifact, session)
        await self.timeline_projector.project(artifact, session)
        await self.relationship_projector.project(artifact, session)
        logger.info(f"Knowledge graph projection complete for {artifact.artifact_id}")
