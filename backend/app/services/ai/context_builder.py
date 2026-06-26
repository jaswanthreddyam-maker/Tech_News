import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.models.article import ProcessedArticle
from app.schemas.ai_context import AIContext, AIContextMetadata, PrivacyLevel
from app.services.ai.budget_allocator import ContextBudgetAllocator
from app.services.ai.providers.article import ArticleProvider
from app.services.ai.providers.behavior import BehaviorProvider
from app.services.ai.providers.citation import CitationProvider
from app.services.ai.providers.knowledge import KnowledgeGraphProvider
from app.services.ai.providers.related import RelatedArticleProvider


class AIContextBuilder:
    def __init__(self):
        self.article_provider = ArticleProvider()
        self.related_provider = RelatedArticleProvider()
        self.behavior_provider = BehaviorProvider()
        self.kg_provider = KnowledgeGraphProvider()
        self.citation_provider = CitationProvider()
        self.allocator = ContextBudgetAllocator()

    async def build(
        self, 
        session: AsyncSession, 
        article_id: int, 
        privacy_level: PrivacyLevel = PrivacyLevel.PUBLIC,
        user_id: int | None = None,
        anonymous_id: str | None = None
    ) -> AIContext:
        """
        Builds, allocates, and caches the AIContext.
        """
        redis = get_redis_client()
        cache_key = f"ai_context:{article_id}:{user_id or 'none'}:{anonymous_id or 'none'}:{privacy_level.value}:v1"

        if redis:
            cached = await redis.get(cache_key)
            if cached:
                # Need to return an AIContext object, but this is a debug method so we rebuild usually.
                # In production, we'd deserialize to AIContext and return.
                try:
                    data = json.loads(cached)
                    return AIContext(**data)
                except Exception:
                    pass

        # 1. Fetch Primary raw article model first to pass to other providers
        stmt = select(ProcessedArticle).where(ProcessedArticle.id == article_id)
        res = await session.execute(stmt)
        raw_article = res.scalar_one_or_none()
        if not raw_article:
            raise ValueError(f"Article {article_id} not found")

        # 2. Invoke Providers
        primary = await self.article_provider.get(session, article_id)
        related = await self.related_provider.get(session, raw_article)
        kg = await self.kg_provider.get(session, raw_article)
        citations = await self.citation_provider.get(session, raw_article)

        behavior = None
        if privacy_level == PrivacyLevel.PERSONALIZED:
            behavior = await self.behavior_provider.get(session, user_id, anonymous_id)

        # 3. Assemble Metadata
        metadata = AIContextMetadata(
            privacy_level=privacy_level,
            article_id=article_id,
            user_id=user_id,
            anonymous_id=anonymous_id
        )

        # 4. Construct Context
        context = AIContext(
            metadata=metadata,
            primary_article=primary,
            related_articles=related,
            knowledge_graph=kg,
            behavior=behavior,
            citations=citations
        )

        # 5. Apply Budget
        context = self.allocator.allocate(context)

        # 6. Cache and Emit Telemetry
        if redis:
            await redis.setex(cache_key, 3600, context.model_dump_json())

            # Telemetry Emission for ADR-0008
            # In a full system, we'd push an AITelemetry event:
            # emit_ai_telemetry(type="context_generated", tokens=context.metadata.token_estimate, ...)

        return context
