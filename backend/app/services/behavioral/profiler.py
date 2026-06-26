import logging
import math
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Category, ProcessedArticle
from app.models.behavioral import ReadingSession, UserInterest

logger = logging.getLogger(__name__)


class InterestScorer:
    """
    Implements multi-factor scoring model:
    Base Score = Completion Score * Reading Time Score * Recency Score
    Aggregate Score = Sum of Base Scores (incorporates Frequency naturally)
    """

    def compute_completion_score(self, completion_percentage: int) -> float:
        if completion_percentage < 25:
            return 0.1
        if completion_percentage < 50:
            return 0.4
        if completion_percentage < 75:
            return 0.7
        return 1.0

    def compute_reading_time_score(self, actual_seconds: int, estimated_minutes: int) -> float:
        if not estimated_minutes or estimated_minutes <= 0:
            estimated_minutes = 3
        estimated_seconds = estimated_minutes * 60
        ratio = actual_seconds / estimated_seconds

        if ratio < 0.2:
            return 0.2
        if ratio < 0.5:
            return 0.5
        if ratio < 0.8:
            return 0.8
        if ratio <= 1.5:
            return 1.0
        return 0.9

    def compute_recency_score(self, occurred_at: datetime) -> float:
        if not occurred_at:
            return 0.1
        age_days = (datetime.now(timezone.utc) - occurred_at).days
        if age_days < 0:
            age_days = 0
        return math.exp(-0.1 * age_days)

    def score_session(self, session: ReadingSession, article: ProcessedArticle) -> float:
        c_score = self.compute_completion_score(session.max_scroll_percent or 0)
        t_score = self.compute_reading_time_score(session.total_reading_seconds or 0, article.reading_time or 3)
        r_score = self.compute_recency_score(session.last_activity_at)

        return c_score * t_score * r_score


class ProfileUpdater:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scorer = InterestScorer()

    async def update_profile_for_user(self, user_id: int | None = None, anonymous_id: str | None = None) -> None:
        if not user_id and not anonymous_id:
            return

        stmt = (
            select(ReadingSession, ProcessedArticle, Category)
            .join(ProcessedArticle, ReadingSession.article_id == ProcessedArticle.id)
            .join(Category, ProcessedArticle.category_id == Category.id)
        )

        if user_id:
            stmt = stmt.where(ReadingSession.user_id == user_id)
        else:
            stmt = stmt.where(ReadingSession.anonymous_id == anonymous_id)

        res = await self.db.execute(stmt)
        sessions_data = res.all()

        if not sessions_data:
            return

        scores = {}  # (entity_type, entity_id) -> total_score
        counts = {}  # (entity_type, entity_id) -> count

        for session, article, category in sessions_data:
            base_score = self.scorer.score_session(session, article)

            # Category
            cat_key = ("CATEGORY", category.name)
            scores[cat_key] = scores.get(cat_key, 0) + base_score
            counts[cat_key] = counts.get(cat_key, 0) + 1

            # Topics (Tags)
            if article.tags:
                tags = [t.strip() for t in article.tags.split(",") if t.strip()]
                for t in tags:
                    topic_key = ("TOPIC", t)
                    scores[topic_key] = scores.get(topic_key, 0) + base_score
                    counts[topic_key] = counts.get(topic_key, 0) + 1

        # Upsert interests
        values_to_insert = []
        for (e_type, e_id), total_score in scores.items():
            count = counts[(e_type, e_id)]
            confidence = min(1.0, count / 5.0)  # Reaches 1.0 confidence at 5+ interactions

            values_to_insert.append(
                {
                    "user_id": user_id,
                    "anonymous_id": anonymous_id if not user_id else None,
                    "entity_type": e_type,
                    "entity_id": e_id,
                    "affinity": total_score,
                    "expertise": 0.0,
                    "confidence": confidence,
                    "model_version": "v1",
                    "last_updated": datetime.now(timezone.utc),
                }
            )

        if values_to_insert:
            # We use PostgreSQL's ON CONFLICT DO UPDATE
            # The unique constraint is on (user_id, entity_type, entity_id) or (anonymous_id, entity_type, entity_id)

            if user_id:
                index_elements = ["user_id", "entity_type", "entity_id"]
            else:
                index_elements = ["anonymous_id", "entity_type", "entity_id"]

            stmt = insert(UserInterest).values(values_to_insert)

            # Exclude None index elements if needed, but PG handles NULL in partial indexes differently.
            # Actually, our Index uses `unique=True`. But PostgreSQL `UNIQUE` constraints with NULLs don't conflict on NULLs.
            # Let's ensure we use the correct constraint logic.
            # We defined: Index('ix_user_interests_user_entity', 'user_id', 'entity_type', 'entity_id', unique=True)

            # This is a bit tricky with asyncpg / sqlalchemy insert on conflict when index has NULL.
            # Let's just delete existing and re-insert for simplicity and robustness since derived state is disposable.

            from sqlalchemy import delete

            del_stmt = delete(UserInterest)
            if user_id:
                del_stmt = del_stmt.where(UserInterest.user_id == user_id)
            else:
                del_stmt = del_stmt.where(UserInterest.anonymous_id == anonymous_id)

            await self.db.execute(del_stmt)

            await self.db.execute(insert(UserInterest), values_to_insert)
            await self.db.commit()
