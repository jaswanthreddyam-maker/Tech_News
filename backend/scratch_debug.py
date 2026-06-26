import asyncio
import uuid
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.projection.context import ProjectionContext
from app.core.projection.executor import ProjectionExecutor
from app.intelligence.search.pipeline import HybridSearchPipeline
from app.intelligence.search.projector import EmbeddingProjector
from app.models.event import EventEnvelope
from app.models.intelligence import SearchIndexNode

# Import all models so relationship mappers are registered
from app.models.source import Source
from app.models.user import User, AIJobHistory, ArticleRevision, AuditLog, Notification, OAuthAccount, Permission, Role, RolePermission, SavedArticle, UserSession
from app.models.article import Category, RawArticle, ProcessedArticle, ArticleReadModel
from app.models.workspace import Workspace, WorkspaceArticle, WorkspaceConversation, WorkspaceNote, WorkspaceNoteVersion, WorkspaceActivity, WorkspaceDigest
from app.models.editorial import PublicationRecord, EditorialDraft, EditorialDecision, DiscussionThread, DraftComment, DraftVersion, EditorialReviewArtifact, EditorialPatch, EditorialSession
from app.models.distribution import DistributionManifest, DistributionJob, DeliveryReport

from unittest.mock import patch, AsyncMock

async def main():
    mock_vector = [0.1] * 1536
    with patch("app.ai.embedding.EmbeddingService.generate_embeddings", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = [mock_vector]

        async with AsyncSessionLocal() as db_session:
            # 1. Project an event into the search index
            projector = EmbeddingProjector()
            context = ProjectionContext(db_session)
            executor = ProjectionExecutor(db_session)

            source_id = f"art_{uuid.uuid4().hex[:8]}"
            print(f"Generated source_id: {source_id}")

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

            print(f"Node found in DB: {node is not None}")
            if node:
                print(f"Node id: {node.id}")
                print(f"Node tsvector: {node.tsvector}")
                print(f"Node embedding (first 5): {node.embedding[:5] if node.embedding is not None else None}")


            # 2. Execute Hybrid Search
            pipeline = HybridSearchPipeline()
            
            # Print retrievers' output directly
            kw_res = await pipeline.keyword_retriever.retrieve(db_session, "PostgreSQL pgvector", limit=10)
            print(f"KeywordRetriever results: {kw_res}")
            
            sem_res = await pipeline.semantic_retriever.retrieve(db_session, "PostgreSQL pgvector", limit=10)
            print(f"SemanticRetriever results: {sem_res}")

            results = await pipeline.execute(db_session, query="PostgreSQL pgvector", limit=10)
            print(f"Pipeline results: {results}")

            found = False
            for res in results:
                if res["document_id"] == source_id:
                    found = True
                    print(f"Found document! matched_via={res['matched_via']}")
                    break

            print(f"Found: {found}")

if __name__ == "__main__":
    asyncio.run(main())
