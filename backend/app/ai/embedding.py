import hashlib
from datetime import datetime, timezone

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.circuit_breaker import CircuitBreaker
from app.ai.schemas import AIJobStatus, AITaskType
from app.core.config import settings
from app.core.redis import get_redis_client
from app.models.article import ProcessedArticle
from app.models.user import AIJobHistory
from app.models.workspace import WorkspaceNote


class EmbeddingService:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
        self.provider = settings.EMBEDDING_PROVIDER
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not self.client:
            raise ValueError("OpenAI client not configured for embeddings.")

        redis_client = get_redis_client()
        cb = CircuitBreaker(redis_client, self.provider)
        if not await cb.can_execute():
            raise RuntimeError(f"Circuit breaker open for embedding provider: {self.provider}")

        try:
            from typing import Any

            # Note: dimensions param is only valid for text-embedding-3 models in OpenAI
            kwargs: dict[str, Any] = {"input": texts, "model": self.model}
            if "text-embedding-3" in self.model:
                kwargs["dimensions"] = self.dimensions

            response = await self.client.embeddings.create(**kwargs)
            await cb.record_success()
            return [data.embedding for data in response.data]
        except Exception as e:
            await cb.record_failure()
            raise e

    def compute_hash(self, title: str, content: str) -> str:
        text = f"{title}\n{content}"
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def process_article_embedding(self, db: AsyncSession, article_id: int) -> bool:
        stmt = select(ProcessedArticle).where(ProcessedArticle.id == article_id)
        res = await db.execute(stmt)
        article = res.scalars().first()

        if not article:
            return False

        current_hash = self.compute_hash(article.title, article.content)

        # Skip generation if we already have the embedding for this content
        if article.embedding_hash == current_hash and article.embedding_status == "completed":
            return True

        # Update status to processing
        article.embedding_status = "processing"
        await db.commit()

        try:
            text_to_embed = f"Title: {article.title}\n\n{article.content}"
            embeddings = await self.generate_embeddings([text_to_embed])

            if not embeddings:
                raise ValueError("No embeddings returned from provider")

            article.embedding = embeddings[0]
            article.embedding_hash = current_hash
            article.embedding_status = "completed"
            article.embedding_updated_at = datetime.now(timezone.utc)

            # Execute Phase 5B Clustering
            from app.ai.clustering import assign_to_cluster

            await assign_to_cluster(db, article)

            # Record telemetry
            job_history = AIJobHistory(
                processed_article_id=article.id,
                task_type=AITaskType.EMBEDDING,
                provider=self.provider,
                model=self.model,
                status=AIJobStatus.COMPLETED,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_usd=0,
                latency_ms=0,
                cache_hit=False,
            )
            db.add(job_history)

            await db.commit()

            # Invalidate semantic cache via generation increment
            from app.core.redis import get_redis_client

            redis = get_redis_client()
            if redis:
                await redis.incr("semantic_generation")

            return True
        except Exception as e:
            # On failure, mark as failed
            article.embedding_status = "failed"

            job_history = AIJobHistory(
                processed_article_id=article.id,
                task_type=AITaskType.EMBEDDING,
                provider=self.provider,
                model=self.model,
                status=AIJobStatus.FAILED,
                error=str(e),
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_usd=0,
                latency_ms=0,
                cache_hit=False,
            )
            db.add(job_history)

            await db.commit()
            raise e

    async def process_note_embedding(self, db: AsyncSession, note_id: int) -> bool:
        stmt = select(WorkspaceNote).where(WorkspaceNote.id == note_id)
        res = await db.execute(stmt)
        note = res.scalars().first()

        if not note:
            return False

        # Embed Title + Summary + Content
        title_str = f"Title: {note.title}\n" if note.title else ""
        summary_str = f"Summary: {note.summary}\n" if note.summary else ""
        text_to_embed = f"{title_str}{summary_str}{note.content}"

        current_hash = self.compute_hash("WorkspaceNote", text_to_embed)

        if note.embedding_hash == current_hash and note.embedding_status == "completed":
            return True

        note.embedding_status = "processing"
        await db.commit()

        try:
            embeddings = await self.generate_embeddings([text_to_embed])

            if not embeddings:
                raise ValueError("No embeddings returned from provider")

            note.embedding = embeddings[0]
            note.embedding_hash = current_hash
            note.embedding_status = "completed"
            note.embedding_updated_at = datetime.now(timezone.utc)
            await db.commit()
            return True
        except Exception as e:
            note.embedding_status = "failed"
            await db.commit()
            raise e
