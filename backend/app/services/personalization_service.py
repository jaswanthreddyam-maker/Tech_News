import logging
from datetime import datetime, timezone

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ArticleReadModel
from app.models.tnt_knowledge import ArticleEntityLink, ArticleTopicLink, EntityNode, TopicNode
from app.models.user import FollowedEntity, FollowedTopic, SavedArticle, UserReadingHistory
from app.schemas.news import ArticleCard

logger = logging.getLogger(__name__)

class PersonalizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def toggle_saved_article(self, user_id: int, article_id: str) -> bool:
        stmt = select(SavedArticle).where(
            SavedArticle.user_id == user_id,
            SavedArticle.article_id == article_id
        )
        result = await self.db.execute(stmt)
        saved = result.scalar_one_or_none()

        if saved:
            await self.db.delete(saved)
            await self.db.commit()
            return False
        else:
            new_save = SavedArticle(user_id=user_id, article_id=article_id)
            self.db.add(new_save)
            await self.db.commit()
            return True

    async def toggle_followed_entity(self, user_id: int, entity_id: str) -> bool:
        stmt = select(FollowedEntity).where(
            FollowedEntity.user_id == user_id,
            FollowedEntity.entity_id == entity_id
        )
        result = await self.db.execute(stmt)
        followed = result.scalar_one_or_none()

        if followed:
            await self.db.delete(followed)
            await self.db.commit()
            return False
        else:
            new_follow = FollowedEntity(user_id=user_id, entity_id=entity_id)
            self.db.add(new_follow)
            await self.db.commit()
            return True

    async def toggle_followed_topic(self, user_id: int, topic_name: str) -> bool:
        stmt = select(FollowedTopic).where(
            FollowedTopic.user_id == user_id,
            FollowedTopic.topic_name == topic_name
        )
        result = await self.db.execute(stmt)
        followed = result.scalar_one_or_none()

        if followed:
            await self.db.delete(followed)
            await self.db.commit()
            return False
        else:
            new_follow = FollowedTopic(user_id=user_id, topic_name=topic_name)
            self.db.add(new_follow)
            await self.db.commit()
            return True

    async def record_reading_history(self, user_id: int, article_id: str, progress: float, completed: bool, reading_time_seconds: int):
        stmt = select(UserReadingHistory).where(
            UserReadingHistory.user_id == user_id,
            UserReadingHistory.article_id == article_id
        )
        result = await self.db.execute(stmt)
        history = result.scalar_one_or_none()

        if history:
            # Update history
            if progress > history.read_progress:
                history.read_progress = progress
            if completed:
                history.completed = True
            history.reading_time_seconds += reading_time_seconds
            history.last_read_at = datetime.now(timezone.utc)
        else:
            history = UserReadingHistory(
                user_id=user_id,
                article_id=article_id,
                read_progress=progress,
                completed=completed,
                reading_time_seconds=reading_time_seconds
            )
            self.db.add(history)

        await self.db.commit()
        return history

    async def get_followed_entities(self, user_id: int):
        stmt = select(EntityNode).join(FollowedEntity, EntityNode.id == FollowedEntity.entity_id).where(FollowedEntity.user_id == user_id)
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_followed_topics(self, user_id: int):
        stmt = select(TopicNode).join(FollowedTopic, TopicNode.name == FollowedTopic.topic_name).where(FollowedTopic.user_id == user_id)
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_personalized_feed(self, user_id: int, limit: int = 20, offset: int = 0):
        # To avoid complex CTEs in pure sqlalchemy without raw SQL, we can fetch matching articles 
        # for user's followed entities and topics, aggregate scores in Python if dataset is small, 
        # or use SQLAlchemy expressions.

        # Subquery for entity matches
        entity_sq = (
            select(
                ArticleEntityLink.article_id,
                func.count().label("entity_match_count"),
                func.array_agg(EntityNode.canonical_name).label("matched_entities")
            )
            .select_from(ArticleEntityLink)
            .join(FollowedEntity, ArticleEntityLink.entity_id == FollowedEntity.entity_id)
            .join(EntityNode, EntityNode.id == ArticleEntityLink.entity_id)
            .where(FollowedEntity.user_id == user_id)
            .group_by(ArticleEntityLink.article_id)
            .subquery()
        )

        # Subquery for topic matches
        topic_sq = (
            select(
                ArticleTopicLink.article_id,
                func.count().label("topic_match_count"),
                func.array_agg(ArticleTopicLink.topic_name).label("matched_topics")
            )
            .select_from(ArticleTopicLink)
            .join(FollowedTopic, ArticleTopicLink.topic_name == FollowedTopic.topic_name)
            .where(FollowedTopic.user_id == user_id)
            .group_by(ArticleTopicLink.article_id)
            .subquery()
        )

        # Main query joining ArticleReadModel with subqueries
        # Only fetch articles that have AT LEAST ONE match
        # Freshness is dynamic: e^(-decay * days_old)

        # Approximate current time
        now_func = func.extract('epoch', func.now())
        pub_func = func.extract('epoch', ArticleReadModel.published_at)
        days_old = (now_func - pub_func) / 86400.0
        # freshness = EXP(-0.3 * days_old)
        freshness_expr = func.exp(-0.3 * days_old)

        entity_score = func.coalesce(entity_sq.c.entity_match_count, 0) * 3
        topic_score = func.coalesce(topic_sq.c.topic_match_count, 0) * 2
        interest_score = entity_score + topic_score

        final_score = interest_score * ArticleReadModel.final_score * freshness_expr


        stmt = (
            select(
                ArticleReadModel,
                entity_sq.c.matched_entities,
                topic_sq.c.matched_topics,
                final_score.label("final_score")
            )
            .outerjoin(entity_sq, ArticleReadModel.id == entity_sq.c.article_id)
            .outerjoin(topic_sq, ArticleReadModel.id == topic_sq.c.article_id)
            .where(
                or_(
                    entity_sq.c.entity_match_count > 0,
                    topic_sq.c.topic_match_count > 0
                )
            )
            .order_by(desc("final_score"))
            .limit(limit)
            .offset(offset)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        feed_items = []
        for row in rows:
            article = row.ArticleReadModel
            matched_entities = row.matched_entities or []
            matched_topics = row.matched_topics or []

            # Remove nulls if any
            matched_entities = [e for e in matched_entities if e]
            matched_topics = [t for t in matched_topics if t]

            reasoning = []
            if matched_entities:
                reasoning.append(f"Entities: {', '.join(matched_entities)}")
            if matched_topics:
                reasoning.append(f"Topics: {', '.join(matched_topics)}")

            feed_items.append({
                "article": ArticleCard.from_model(article, topics=matched_topics, entities=matched_entities),
                "reasoning_metadata": {
                    "matched_entities": matched_entities,
                    "matched_topics": matched_topics,
                    "message": "Because you follow " + " and ".join(reasoning) if reasoning else ""
                },
                "score": float(row.final_score) if row.final_score is not None else 0.0
            })

        return feed_items
