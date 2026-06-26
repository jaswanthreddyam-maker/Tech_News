import logging
from typing import Any

# In a real setup, this would be an injected dependency. We'll mock embedding for this sprint.
from app.ai.embedding import EmbeddingService
from app.core.projection.context import ProjectionContext
from app.core.projection.mutations import InsertMutation, ProjectionBatch, SetMutation
from app.core.projection.projector import Projector
from app.models.event import EventEnvelope
from app.models.intelligence import SearchIndexNode
from app.models.user import utc_now

logger = logging.getLogger(__name__)

class EmbeddingProjector(Projector):
    def __init__(self):
        self.embedding_service = EmbeddingService()

    @property
    def projection_group(self) -> str:
        return "intelligence_search"

    @property
    def name(self) -> str:
        return "EmbeddingProjector"

    @property
    def version(self) -> int:
        return 1

    @property
    def supported_events(self) -> list[str]:
        # Events that trigger search index updates
        return [
            "ARTICLE_PUBLISHED",
            "ARTICLE_UPDATED",
            "WORKSPACE_CREATED",
            "WORKSPACE_UPDATED"
        ]

    async def _generate_embeddings(self, text: str) -> list[float]:
        try:
            vectors = await self.embedding_service.generate_embeddings([text])
            return vectors[0]
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            # Mock fallback for sprint
            return [0.0] * 1536

    def _convert_to_tsvector(self, text: str) -> Any:
        from sqlalchemy import func
        # This will be processed by the DB on insert/update.
        return func.to_tsvector('english', text)

    async def project(self, event: EventEnvelope, context: ProjectionContext) -> ProjectionBatch:
        batch = ProjectionBatch(version=self.version)
        now = utc_now()

        payload = event.payload or {}

        node_type = None
        source_id = None
        title = ""
        content = ""
        workspace_id = None
        visibility = "PUBLIC"

        if event.event_type in ["ARTICLE_PUBLISHED", "ARTICLE_UPDATED"]:
            node_type = "ARTICLE"
            source_id = str(payload.get("article_id"))
            title = payload.get("title", "")
            content = payload.get("content", "")
            visibility = "PUBLIC"

        elif event.event_type in ["WORKSPACE_CREATED", "WORKSPACE_UPDATED"]:
            node_type = "WORKSPACE"
            source_id = str(payload.get("workspace_id"))
            title = payload.get("name", "")
            content = payload.get("description", "")
            workspace_id = payload.get("workspace_id")
            visibility = "PRIVATE"

        if not node_type or not source_id:
            return batch

        # Check if node exists
        node = await context.load(SearchIndexNode, {"node_type": node_type, "source_id": source_id})

        text_to_embed = f"{title}\n\n{content}"
        embedding = await self._generate_embeddings(text_to_embed)

        from sqlalchemy import func

        if node:
            batch.add(SetMutation(model=SearchIndexNode, target_id=node.id, field="title", value=title))
            batch.add(SetMutation(model=SearchIndexNode, target_id=node.id, field="content", value=content))
            batch.add(SetMutation(model=SearchIndexNode, target_id=node.id, field="embedding", value=embedding))
            batch.add(SetMutation(model=SearchIndexNode, target_id=node.id, field="embedding_generated_at", value=now))
            # SQLAlchemy handles func expressions natively in SetMutation if adapted, 
            # but since SetMutation is simple dictionary updates, we can update it in a direct query or let UPE handle it.
            batch.add(SetMutation(model=SearchIndexNode, target_id=node.id, field="tsvector", value=func.to_tsvector('english', text_to_embed)))
        else:
            batch.add(InsertMutation(
                model=SearchIndexNode,
                values={
                    "node_type": node_type,
                    "source_id": source_id,
                    "title": title,
                    "content": content,
                    "embedding": embedding,
                    "tsvector": func.to_tsvector('english', text_to_embed),
                    "workspace_id": workspace_id,
                    "visibility": visibility,
                    "embedding_model": "text-embedding-3-small",
                    "embedding_version": "v1.0",
                    "embedding_generated_at": now
                }
            ))

        return batch

from app.core.projection.registry import projector_registry

projector_registry.register(EmbeddingProjector())
