from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ProcessedArticle
from app.schemas.ai_context import ContextKnowledgeGraph


class KnowledgeGraphProvider:
    async def get(self, session: AsyncSession, article: ProcessedArticle) -> ContextKnowledgeGraph:
        # Mock/stub implementation
        # In the future, this will query the actual Knowledge Graph based on the article's entities
        nodes = []
        # ProcessedArticle doesn't have a direct 'entities' field, use getattr safely
        entities = getattr(article, "entities", None) or []
        for entity in entities:
            nodes.append({"id": entity, "type": "Entity", "relevance": "high"})

        return ContextKnowledgeGraph(
            nodes=nodes,
            relationships=[]
        )
