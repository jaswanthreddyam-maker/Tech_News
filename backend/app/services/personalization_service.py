from datetime import datetime, timezone
import logging

from sqlalchemy import cast, desc, func, or_, select, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ArticleReadModel, ProcessedArticle
from app.models.followed_source import FollowedSource
from app.models.source import Source
from app.models.tnt_knowledge import ArticleEntityLink, ArticleTopicLink, EntityNode, TopicNode
from app.models.user import FollowedEntity, FollowedTopic, SavedArticle, UserReadingHistory
from app.schemas.news import ArticleCard

logger = logging.getLogger(__name__)


class PersonalizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # -----------------------------------------------------------------------
    # Source Following Domain Logic
    # -----------------------------------------------------------------------

    async def list_sources(self, user_id: int | None = None) -> list[dict]:
        """
        List all active, non-deleted sources with their followed status for user_id.
        """
        stmt = (
            select(Source)
            .where(Source.enabled == True, Source.is_deleted == False)
            .order_by(
                Source.category.asc(),
                Source.name.asc(),
            )
        )
        res = await self.db.execute(stmt)
        sources = res.scalars().all()

        followed_ids = set()
        if user_id:
            follow_stmt = select(FollowedSource.source_id).where(FollowedSource.user_id == user_id)
            follow_res = await self.db.execute(follow_stmt)
            followed_ids = set(follow_res.scalars().all())

        return [
            {
                "id": s.id,
                "name": s.name,
                "slug": s.slug or str(s.id),
                "category": s.category,
                "description": s.description,
                "logo_url": s.logo_url,
                "url": s.url,
                "credibility_score": s.credibility_score,
                "is_following": s.id in followed_ids,
            }
            for s in sources
        ]

    async def _resolve_source_by_slug(self, source_slug: str) -> Source | None:
        """
        Resolves an active Source entity strictly by its canonical slug.
        Numeric ID fallback is strictly forbidden.
        """
        if not source_slug or not isinstance(source_slug, str):
            return None
        normalized_slug = source_slug.strip().lower()
        stmt = select(Source).where(
            Source.slug == normalized_slug,
            Source.enabled == True,
            Source.is_deleted == False,
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def follow_source(self, user_id: int, source_slug: str) -> bool:
        """
        Idempotently follow an active source strictly by canonical slug.
        Raises ValueError if the source does not exist or is inactive/deleted.
        """
        source = await self._resolve_source_by_slug(source_slug)
        if not source:
            raise ValueError(f"Source with slug '{source_slug}' does not exist or is inactive.")

        existing_stmt = select(FollowedSource).where(
            FollowedSource.user_id == user_id,
            FollowedSource.source_id == source.id,
        )
        existing = (await self.db.execute(existing_stmt)).scalar_one_or_none()
        if not existing:
            new_follow = FollowedSource(user_id=user_id, source_id=source.id)
            self.db.add(new_follow)
            await self.db.commit()
        return True

    async def unfollow_source(self, user_id: int, source_slug: str) -> bool:
        """
        Idempotently unfollow a source strictly by canonical slug.
        """
        source = await self._resolve_source_by_slug(source_slug)
        if not source:
            return False

        stmt = select(FollowedSource).where(
            FollowedSource.user_id == user_id,
            FollowedSource.source_id == source.id,
        )
        res = await self.db.execute(stmt)
        record = res.scalar_one_or_none()
        if record:
            await self.db.delete(record)
            await self.db.commit()
        return False

    async def get_followed_source_ids(self, user_id: int) -> list[int]:
        stmt = (
            select(FollowedSource.source_id)
            .join(Source, FollowedSource.source_id == Source.id)
            .where(
                FollowedSource.user_id == user_id,
                Source.enabled == True,
                Source.is_deleted == False,
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_followed_source_slugs(self, user_id: int) -> list[str]:
        stmt = (
            select(Source.slug)
            .join(FollowedSource, FollowedSource.source_id == Source.id)
            .where(
                FollowedSource.user_id == user_id,
                Source.enabled == True,
                Source.is_deleted == False,
            )
        )
        res = await self.db.execute(stmt)
        return [s for s in res.scalars().all() if s]

    async def sync_guest_follows(
        self,
        user_id: int,
        source_slugs: list[str] | None = None,
    ) -> list[str]:
        """
        Bulk merge guest follows (canonical slugs) into the user's account upon sign-in.
        Returns the updated list of followed source slugs.
        """
        if source_slugs:
            normalized_slugs = [s.strip().lower() for s in source_slugs if s and isinstance(s, str)]
            if normalized_slugs:
                stmt = select(Source.id).where(
                    Source.slug.in_(normalized_slugs),
                    Source.enabled == True,
                    Source.is_deleted == False,
                )
                res = await self.db.execute(stmt)
                target_ids = set(res.scalars().all())

                if target_ids:
                    existing_stmt = select(FollowedSource.source_id).where(
                        FollowedSource.user_id == user_id,
                        FollowedSource.source_id.in_(target_ids),
                    )
                    existing_ids = set((await self.db.execute(existing_stmt)).scalars().all())

                    new_ids = target_ids - existing_ids
                    for s_id in new_ids:
                        self.db.add(FollowedSource(user_id=user_id, source_id=s_id))

                    if new_ids:
                        await self.db.commit()

        return await self.get_followed_source_slugs(user_id)

    async def get_source_following_feed(
        self,
        user_id: int | None = None,
        guest_source_slugs: list[str] | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> dict:
        """
        Returns articles published strictly by the user's followed sources,
        ordered chronologically (published_at DESC, id DESC).
        Invariant: FOLLOWED_SOURCE_IDS = ∅ => feed = [] (never fallback to latest/global).
        """
        followed_source_ids = []
        if user_id:
            followed_source_ids = await self.get_followed_source_ids(user_id)
        elif guest_source_slugs:
            normalized_slugs = [s.strip().lower() for s in guest_source_slugs if s and isinstance(s, str)]
            if normalized_slugs:
                slug_stmt = select(Source.id).where(
                    Source.slug.in_(normalized_slugs),
                    Source.enabled == True,
                    Source.is_deleted == False,
                )
                followed_source_ids = list((await self.db.execute(slug_stmt)).scalars().all())

        if not followed_source_ids:
            return {
                "items": [],
                "followed_sources_count": 0,
                "total": 0,
            }

        now_utc = datetime.now(timezone.utc)

        # Count total
        count_stmt = (
            select(func.count(ProcessedArticle.id))
            .join(ArticleReadModel, ArticleReadModel.id == cast(ProcessedArticle.id, String))
            .join(Source, ProcessedArticle.source_id == Source.id)
            .where(
                ProcessedArticle.source_id.in_(followed_source_ids),
                Source.enabled == True,
                Source.is_deleted == False,
                ArticleReadModel.publication_status == "PUBLISHED",
                ArticleReadModel.is_test_data == False,
                or_(ProcessedArticle.is_archived == None, ProcessedArticle.is_archived == False),
                or_(ProcessedArticle.is_expired == None, ProcessedArticle.is_expired == False),
                or_(ProcessedArticle.expires_at == None, ProcessedArticle.expires_at > now_utc),
            )
        )
        total_count = (await self.db.execute(count_stmt)).scalar() or 0

        # Query items
        stmt = (
            select(ArticleReadModel, ProcessedArticle, Source)
            .join(ArticleReadModel, ArticleReadModel.id == cast(ProcessedArticle.id, String))
            .join(Source, ProcessedArticle.source_id == Source.id)
            .where(
                ProcessedArticle.source_id.in_(followed_source_ids),
                Source.enabled == True,
                Source.is_deleted == False,
                ArticleReadModel.publication_status == "PUBLISHED",
                ArticleReadModel.is_test_data == False,
                or_(ProcessedArticle.is_archived == None, ProcessedArticle.is_archived == False),
                or_(ProcessedArticle.is_expired == None, ProcessedArticle.is_expired == False),
                or_(ProcessedArticle.expires_at == None, ProcessedArticle.expires_at > now_utc),
            )
            .order_by(
                ProcessedArticle.published_at.desc(),
                ProcessedArticle.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        res = await self.db.execute(stmt)
        rows = res.all()

        article_cards = []
        for row in rows:
            read_model = row.ArticleReadModel
            src = row.Source
            card = ArticleCard.from_model(read_model)
            card.source = src.name
            article_cards.append(card)

        return {
            "items": article_cards,
            "followed_sources_count": len(followed_source_ids),
            "total": total_count,
        }

    # -----------------------------------------------------------------------
    # Saved Articles, Entities & Topics
    # -----------------------------------------------------------------------

    async def toggle_saved_article(self, user_id: int, article_id: str) -> bool:
        stmt = select(SavedArticle).where(
            SavedArticle.user_id == user_id,
            SavedArticle.article_id == article_id,
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
            FollowedEntity.entity_id == entity_id,
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
            FollowedTopic.topic_name == topic_name,
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

    async def record_reading_history(
        self, user_id: int, article_id: str, progress: float, completed: bool, reading_time_seconds: int
    ):
        stmt = select(UserReadingHistory).where(
            UserReadingHistory.user_id == user_id,
            UserReadingHistory.article_id == article_id,
        )
        result = await self.db.execute(stmt)
        history = result.scalar_one_or_none()

        if history:
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
                reading_time_seconds=reading_time_seconds,
            )
            self.db.add(history)

        await self.db.commit()
        return history

    async def get_followed_entities(self, user_id: int):
        stmt = (
            select(EntityNode)
            .join(FollowedEntity, EntityNode.id == FollowedEntity.entity_id)
            .where(FollowedEntity.user_id == user_id)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_followed_topics(self, user_id: int):
        stmt = (
            select(TopicNode)
            .join(FollowedTopic, TopicNode.name == FollowedTopic.topic_name)
            .where(FollowedTopic.user_id == user_id)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def get_personalized_feed(self, user_id: int, limit: int = 20, offset: int = 0):
        entity_sq = (
            select(
                ArticleEntityLink.article_id,
                func.count().label("entity_match_count"),
                func.array_agg(EntityNode.canonical_name).label("matched_entities"),
            )
            .select_from(ArticleEntityLink)
            .join(FollowedEntity, ArticleEntityLink.entity_id == FollowedEntity.entity_id)
            .join(EntityNode, EntityNode.id == ArticleEntityLink.entity_id)
            .where(FollowedEntity.user_id == user_id)
            .group_by(ArticleEntityLink.article_id)
            .subquery()
        )

        topic_sq = (
            select(
                ArticleTopicLink.article_id,
                func.count().label("topic_match_count"),
                func.array_agg(ArticleTopicLink.topic_name).label("matched_topics"),
            )
            .select_from(ArticleTopicLink)
            .join(FollowedTopic, ArticleTopicLink.topic_name == FollowedTopic.topic_name)
            .where(FollowedTopic.user_id == user_id)
            .group_by(ArticleTopicLink.article_id)
            .subquery()
        )

        now_func = func.extract("epoch", func.now())
        pub_func = func.extract("epoch", ArticleReadModel.published_at)
        days_old = (now_func - pub_func) / 86400.0
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
                final_score.label("final_score"),
            )
            .outerjoin(entity_sq, ArticleReadModel.id == entity_sq.c.article_id)
            .outerjoin(topic_sq, ArticleReadModel.id == topic_sq.c.article_id)
            .where(
                or_(
                    entity_sq.c.entity_match_count > 0,
                    topic_sq.c.topic_match_count > 0,
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

            matched_entities = [e for e in matched_entities if e]
            matched_topics = [t for t in matched_topics if t]

            reasoning = []
            if matched_entities:
                reasoning.append(f"Entities: {', '.join(matched_entities)}")
            if matched_topics:
                reasoning.append(f"Topics: {', '.join(matched_topics)}")

            feed_items.append(
                {
                    "article": ArticleCard.from_model(article, topics=matched_topics, entities=matched_entities),
                    "reasoning_metadata": {
                        "matched_entities": matched_entities,
                        "matched_topics": matched_topics,
                        "message": "Because you follow " + " and ".join(reasoning) if reasoning else "",
                    },
                    "score": float(row.final_score) if row.final_score is not None else 0.0,
                }
            )

        return feed_items
