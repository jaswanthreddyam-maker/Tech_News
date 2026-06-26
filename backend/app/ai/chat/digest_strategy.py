import logging
from datetime import datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chat.retrieval_strategy import BaseRetrievalStrategy
from app.ai.ranking import rank_semantic_results
from app.models.article import ProcessedArticle
from app.models.workspace import WorkspaceActivity, WorkspaceArticle, WorkspaceNote

logger = logging.getLogger("tech_news.ai.chat.digest_strategy")


class InternalCollector:
    @staticmethod
    async def collect(
        workspace_id: int, since_time: datetime, until_time: datetime, db: AsyncSession
    ) -> dict[str, list[Any]]:
        # Collect activities
        stmt = (
            select(WorkspaceActivity)
            .where(
                and_(
                    WorkspaceActivity.workspace_id == workspace_id,
                    WorkspaceActivity.created_at >= since_time,
                    WorkspaceActivity.created_at <= until_time,
                )
            )
            .order_by(WorkspaceActivity.created_at)
        )
        activities_res = await db.execute(stmt)
        activities = activities_res.scalars().all()

        # Collect updated notes
        stmt = select(WorkspaceNote).where(
            and_(
                WorkspaceNote.workspace_id == workspace_id,
                WorkspaceNote.updated_at >= since_time,
                WorkspaceNote.updated_at <= until_time,
            )
        )
        notes_res = await db.execute(stmt)
        notes = notes_res.scalars().all()

        # Collect pinned articles
        stmt = (
            select(ProcessedArticle)
            .join(WorkspaceArticle, WorkspaceArticle.article_id == ProcessedArticle.id)
            .where(
                and_(
                    WorkspaceArticle.workspace_id == workspace_id,
                    WorkspaceArticle.created_at >= since_time,
                    WorkspaceArticle.created_at <= until_time,
                )
            )
        )
        articles_res = await db.execute(stmt)
        articles = articles_res.scalars().all()

        return {"activities": activities, "notes": notes, "articles": articles}


class ExternalCollector:
    @staticmethod
    async def collect(
        workspace_id: int, since_time: datetime, until_time: datetime, db: AsyncSession
    ) -> list[ProcessedArticle]:
        # Calculate weighted workspace embedding
        # Weighting: Notes 40%, Articles 35%, Conversations 15%, Comparisons 10%
        # For simplicity in this implementation, we will fetch notes and articles
        # and average them. If we have no embeddings, return empty.

        stmt_notes = select(WorkspaceNote.embedding).where(
            and_(WorkspaceNote.workspace_id == workspace_id, WorkspaceNote.embedding.is_not(None))
        )
        notes_res = await db.execute(stmt_notes)
        note_embeddings = [r[0] for r in notes_res.all() if r[0] is not None]

        stmt_arts = (
            select(ProcessedArticle.embedding)
            .join(WorkspaceArticle, WorkspaceArticle.article_id == ProcessedArticle.id)
            .where(and_(WorkspaceArticle.workspace_id == workspace_id, ProcessedArticle.embedding.is_not(None)))
        )
        arts_res = await db.execute(stmt_arts)
        art_embeddings = [r[0] for r in arts_res.all() if r[0] is not None]

        if not note_embeddings and not art_embeddings:
            return []

        import numpy as np

        # 40% notes, 35% articles (normalized out of their total sum if others are missing)
        notes_arr = np.array(note_embeddings) if note_embeddings else np.zeros((1, 1536))
        arts_arr = np.array(art_embeddings) if art_embeddings else np.zeros((1, 1536))

        avg_note = np.mean(notes_arr, axis=0) if note_embeddings else np.zeros(1536)
        avg_art = np.mean(arts_arr, axis=0) if art_embeddings else np.zeros(1536)

        w_note = 0.40 if note_embeddings else 0.0
        w_art = 0.35 if art_embeddings else 0.0

        total_w = w_note + w_art
        if total_w == 0:
            return []

        workspace_vector = (avg_note * (w_note / total_w)) + (avg_art * (w_art / total_w))
        workspace_vector = workspace_vector.tolist()

        # Search for external news published after since_time
        distance_col = ProcessedArticle.embedding.cosine_distance(workspace_vector).label("distance")
        stmt = (
            select(ProcessedArticle, distance_col)
            .where(and_(ProcessedArticle.published_at >= since_time, ProcessedArticle.embedding.is_not(None)))
            .order_by(distance_col)
            .limit(20)
        )

        res = await db.execute(stmt)
        matches = []
        for row in res:
            score = 1.0 - float(row.distance)
            if score > 0.65:  # Basic relevance threshold
                matches.append((row.ProcessedArticle, score))

        # Rank results
        ranked = rank_semantic_results("news updates", matches)
        return [r["article"] for r in ranked[:8]]


class DigestRetrievalStrategy(BaseRetrievalStrategy):
    """
    Retrieves context for generating a Daily Digest.
    """

    async def retrieve(self, query: str, db: AsyncSession, **kwargs) -> list[dict[str, Any]]:
        workspace_id = kwargs.get("workspace_id")
        since_time = kwargs.get("since_time")
        until_time = kwargs.get("until_time")

        if not all([workspace_id, since_time, until_time]):
            logger.warning("DigestRetrievalStrategy requires workspace_id, since_time, and until_time.")
            return []

        internal_data = await InternalCollector.collect(workspace_id, since_time, until_time, db)
        external_articles = await ExternalCollector.collect(workspace_id, since_time, until_time, db)

        output = []

        # Package Internal
        for note in internal_data["notes"]:
            output.append(
                {
                    "type": "internal_note",
                    "id": f"note_{note.id}",
                    "title": note.title or "Untitled Note",
                    "content": note.content,
                }
            )

        for art in internal_data["articles"]:
            output.append(
                {
                    "type": "internal_article",
                    "id": f"art_{art.id}",
                    "title": art.title,
                    "content": art.summary or art.content,
                }
            )

        # We also pass activity summaries just to give LLM context
        activity_strings = []
        for act in internal_data["activities"]:
            act_str = f"[{act.created_at.strftime('%H:%M')}] {act.event_type} - {act.resource_type} {act.resource_id}"
            activity_strings.append(act_str)

        if activity_strings:
            output.append(
                {
                    "type": "internal_activity",
                    "id": "activity_log",
                    "title": "Workspace Activity Log",
                    "content": "\n".join(activity_strings),
                }
            )

        # Package External
        for art in external_articles:
            output.append(
                {
                    "type": "external_article",
                    "id": f"ext_{art.id}",
                    "title": art.title,
                    "content": art.summary or art.content,
                    "url": art.url,
                }
            )

        # Metadata payload side-channel (will be picked up by DigestService)
        # We use a special type 'metadata' to pass this back up
        output.append(
            {
                "type": "metadata",
                "payload": {
                    "new_articles": len(internal_data["articles"]),
                    "new_notes": len(internal_data["notes"]),
                    "new_comparisons": sum(
                        1 for a in internal_data["activities"] if a.event_type == "COMPARISON_CREATED"
                    ),
                    "external_matches": len(external_articles),
                },
            }
        )

        return output
