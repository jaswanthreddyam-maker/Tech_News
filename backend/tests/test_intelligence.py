import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.projection.context import ProjectionContext
from app.core.projection.executor import ProjectionExecutor
from app.intelligence.search.pipeline import HybridSearchPipeline
from app.intelligence.search.projector import EmbeddingProjector
from app.models.event import EventEnvelope
from app.models.intelligence import SearchIndexNode

# Ensure all models are imported so that SQLAlchemy mapping is fully resolved
from app.models.source import Source
from app.models.user import User, AIJobHistory, ArticleRevision, AuditLog, Notification, OAuthAccount, Permission, Role, RolePermission, SavedArticle, UserSession
from app.models.article import Category, RawArticle, ProcessedArticle, ArticleReadModel
from app.models.workspace import Workspace, WorkspaceArticle, WorkspaceConversation, WorkspaceNote, WorkspaceNoteVersion, WorkspaceActivity, WorkspaceDigest
from app.models.editorial import PublicationRecord, EditorialDraft, EditorialDecision, DiscussionThread, DraftComment, DraftVersion, EditorialReviewArtifact, EditorialPatch, EditorialSession
from app.models.distribution import DistributionManifest, DistributionJob, DeliveryReport


@pytest.mark.asyncio
async def test_hybrid_search_pipeline(db_session: AsyncSession):
    # Clean up table for isolated test
    await db_session.execute(SearchIndexNode.__table__.delete())
    await db_session.commit()

    from unittest.mock import patch, AsyncMock

    mock_vector = [0.1] * 1536
    with patch("app.ai.embedding.EmbeddingService.generate_embeddings", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = [mock_vector]

        # 1. Project an event into the search index
        projector = EmbeddingProjector()
        context = ProjectionContext(db_session)
        executor = ProjectionExecutor(db_session)

        source_id = f"art_{uuid.uuid4().hex[:8]}"

        event = EventEnvelope(
            event_type="ARTICLE_PUBLISHED",
            subject_id="system",
            payload={
                "article_id": source_id,
                "title": "PostgreSQL pgvector for AI",
                "content": "A deep dive into building hybrid search with TSVECTOR and embeddings."
            }
        )

        batch = await projector.project(event, context)
        await executor.execute_batch(batch)
        await db_session.commit()

        # Verify insertion
        node = (await db_session.execute(
            select(SearchIndexNode).where(SearchIndexNode.source_id == source_id)
        )).scalar_one_or_none()

        assert node is not None
        assert node.tsvector is not None
        assert node.embedding is not None

        # 2. Execute Hybrid Search
        pipeline = HybridSearchPipeline()
        results = await pipeline.execute(db_session, query="PostgreSQL pgvector", limit=10)

        # Should find our document via HYBRID matched_via (since both semantic and keyword mock will hit it, or at least one will)
        found = False
        for res in results:
            if res["document_id"] == source_id:
                found = True
                assert res["matched_via"] in ["KEYWORD", "SEMANTIC", "HYBRID"]
                break

        assert found
