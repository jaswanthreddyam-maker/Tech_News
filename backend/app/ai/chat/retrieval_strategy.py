import logging
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chat.retrieval import RetrievalEngine
from app.ai.chat.schemas import ComparisonContext, ConversationMode
from app.ai.embedding import EmbeddingService
from app.ai.ranking import rank_semantic_results
from app.models.article import ArticleReadModel
from app.models.tnt_knowledge import (
    ArticleEntityLink,
    ArticleTopicLink,
    EntityNode,
    RelationshipEdge,
    TimelineEventNode,
    TopicNode,
)
from app.models.workspace import WorkspaceArticle, WorkspaceNote

logger = logging.getLogger("tech_news.ai.chat.retrieval_strategy")


class BaseRetrievalStrategy(ABC):
    """Abstract base class for all retrieval strategies."""

    def __init__(self):
        self.engine = RetrievalEngine()

    @abstractmethod
    async def retrieve(self, query: str, db: AsyncSession, **kwargs) -> list[dict[str, Any]]:
        """Executes the retrieval logic and returns a list of article dicts."""
        pass


class GeneralRetrievalStrategy(BaseRetrievalStrategy):
    """Retrieves context using a standard semantic search over the corpus."""

    async def retrieve(self, query: str, db: AsyncSession, **kwargs) -> list[dict[str, Any]]:
        return await self.engine.retrieve(query=query, db=db, limit=10)


class ArticleRetrievalStrategy(BaseRetrievalStrategy):
    """Retrieves context specifically locked to a given article ID, and includes its knowledge graph."""

    async def retrieve(self, query: str, db: AsyncSession, **kwargs) -> list[dict[str, Any]]:
        article_id = kwargs.get("article_id")
        if not article_id:
            logger.warning("ArticleRetrievalStrategy called without article_id, falling back to general.")
            return await self.engine.retrieve(query=query, db=db, limit=10)

        # 1. Fetch the main article
        articles = await self.engine.retrieve(query=query, db=db, limit=1, article_id=article_id)
        if not articles:
            return []

        output = []
        output.extend(articles)

        # 2. Fetch entities
        stmt_ent = select(EntityNode).join(ArticleEntityLink).where(ArticleEntityLink.article_id == article_id)
        for ent in (await db.execute(stmt_ent)).scalars().all():
            output.append({"type": "entity", "id": ent.id, "title": ent.canonical_name, "description": ent.description})

        # 3. Fetch topics
        stmt_top = select(TopicNode).join(ArticleTopicLink).where(ArticleTopicLink.article_id == article_id)
        for top in (await db.execute(stmt_top)).scalars().all():
            output.append({"type": "topic", "id": top.name, "title": top.name, "description": f"Category: {top.taxonomy_category}"})

        # 4. Fetch timeline events
        stmt_time = select(TimelineEventNode).where(TimelineEventNode.article_id == article_id)
        for evt in (await db.execute(stmt_time)).scalars().all():
            output.append({"type": "timeline_event", "id": evt.id, "title": f"{evt.date} - {evt.event_type}", "description": evt.description})

        # 5. Fetch relationships
        stmt_rel = select(RelationshipEdge).where(RelationshipEdge.article_id == article_id)
        for rel in (await db.execute(stmt_rel)).scalars().all():
            output.append({"type": "relationship", "id": rel.id, "title": f"{rel.source_id} {rel.predicate} {rel.target_id}", "description": ""})

        return output


class ComparisonRetrievalStrategy(BaseRetrievalStrategy):
    """
    Retrieves entities/topics first, then articles to perform dual independent retrieval.
    """

    async def _resolve_context_query(self, context: ComparisonContext | None, fallback_query: str, db: AsyncSession) -> list[dict]:
        if not context:
            return []

        results = []
        if context.type == "entity":
            stmt = select(EntityNode).where(EntityNode.id == context.value)
            ent = (await db.execute(stmt)).scalars().first()
            if ent:
                results.append({"type": "entity", "id": ent.id, "title": ent.canonical_name, "description": ent.description})
                # Fetch recent articles for this entity
                art_stmt = select(ArticleReadModel).join(ArticleEntityLink).where(ArticleEntityLink.entity_id == ent.id).limit(5)
                for art in (await db.execute(art_stmt)).scalars().all():
                    results.append({"type": "article", "id": art.id, "title": art.title, "content": art.content})
        elif context.type == "topic":
            stmt = select(TopicNode).where(TopicNode.name == context.value)
            top = (await db.execute(stmt)).scalars().first()
            if top:
                results.append({"type": "topic", "id": top.name, "title": top.name, "description": f"Category: {top.taxonomy_category}"})
                art_stmt = select(ArticleReadModel).join(ArticleTopicLink).where(ArticleTopicLink.topic_name == top.name).limit(5)
                for art in (await db.execute(art_stmt)).scalars().all():
                    results.append({"type": "article", "id": art.id, "title": art.title, "content": art.content})
        else:
            # Fallback to general semantic search for the value
            arts = await self.engine.retrieve(query=context.value, db=db, limit=5)
            results.extend(arts)

        return results

    async def retrieve(self, query: str, db: AsyncSession, **kwargs) -> list[dict[str, Any]]:
        context_a: ComparisonContext | None = kwargs.get("context_a")
        context_b: ComparisonContext | None = kwargs.get("context_b")

        results_a = await self._resolve_context_query(context_a, query, db)
        results_b = await self._resolve_context_query(context_b, query, db)

        # Merge and deduplicate by type+id
        seen_ids = set()
        merged = []

        max_len = max(len(results_a), len(results_b))
        for i in range(max_len):
            if i < len(results_a):
                item_a = results_a[i]
                key_a = f"{item_a.get('type')}_{item_a.get('id')}"
                if key_a not in seen_ids:
                    seen_ids.add(key_a)
                    merged.append(item_a)
            if i < len(results_b):
                item_b = results_b[i]
                key_b = f"{item_b.get('type')}_{item_b.get('id')}"
                if key_b not in seen_ids:
                    seen_ids.add(key_b)
                    merged.append(item_b)

        return merged[:20]


class WorkspaceRetrievalStrategy(BaseRetrievalStrategy):
    """
    Retrieves context strictly from a user's Research Workspace.
    Limits semantic search to pinned articles and includes workspace notes.
    """

    def __init__(self):
        super().__init__()
        self.embedding_service = EmbeddingService()

    async def retrieve(self, query: str, db: AsyncSession, **kwargs) -> list[dict[str, Any]]:
        workspace_id = kwargs.get("workspace_id")
        if not workspace_id:
            logger.warning("WorkspaceRetrievalStrategy called without workspace_id, returning empty.")
            return []

        try:
            vectors = await self.embedding_service.generate_embeddings([query])
            query_vector = vectors[0]
        except Exception as e:
            logger.error(f"Workspace Retrieval Engine: Failed to generate embedding: {e}")
            return []

        distance_col = ArticleReadModel.embedding.cosine_distance(query_vector).label("distance")

        # 1. Retrieve pinned articles via Semantic Search
        stmt = (
            select(ArticleReadModel, distance_col)
            .join(WorkspaceArticle, WorkspaceArticle.article_id == ArticleReadModel.id)
            .where(and_(WorkspaceArticle.workspace_id == workspace_id, ArticleReadModel.embedding != None))
            .order_by(distance_col)
            .limit(15)  # Fetch top 15 from workspace
        )

        db_results = await db.execute(stmt)
        semantic_matches = []
        for row in db_results:
            article = row.ArticleReadModel
            semantic_score = 1.0 - float(row.distance)
            semantic_matches.append((article, semantic_score))

        # Rank them
        ranked_results = rank_semantic_results(query, semantic_matches)

        output = []
        for rank_item in ranked_results[:8]:  # Return top 8 articles
            art = rank_item["article"]
            output.append(
                {
                    "type": "article",
                    "id": art.id,
                    "title": art.title,
                    "content": art.content or art.summary,
                    "url": art.url,
                    "score": round(rank_item["final_score"], 4),
                }
            )

        # 2. Retrieve Workspace Notes (load all notes for now as they are text snippets)
        notes_stmt = select(WorkspaceNote).where(WorkspaceNote.workspace_id == workspace_id)
        notes_res = await db.execute(notes_stmt)
        for note in notes_res.scalars().all():
            output.append(
                {
                    "type": "note",
                    "id": f"note_{note.id}",
                    "title": f"Workspace Note (Updated: {note.updated_at.strftime('%Y-%m-%d')})",
                    "content": note.content,
                    "url": None,
                    "score": 1.0,  # Notes are explicitly added by user, high relevance
                }
            )

        # Future: We could also fetch past conversation summaries here

        return output


class RetrievalStrategyFactory:
    @staticmethod
    def get_strategy(mode: ConversationMode) -> BaseRetrievalStrategy:
        if mode == ConversationMode.COMPARISON:
            return ComparisonRetrievalStrategy()
        elif mode == ConversationMode.ARTICLE:
            return ArticleRetrievalStrategy()
        elif mode == ConversationMode.WORKSPACE:
            return WorkspaceRetrievalStrategy()
        else:
            return GeneralRetrievalStrategy()
