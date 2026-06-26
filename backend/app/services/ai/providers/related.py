
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ProcessedArticle
from app.schemas.ai_context import ContextRelatedArticle


class RelatedArticleProvider:
    async def get(self, session: AsyncSession, article: ProcessedArticle, limit: int = 5) -> list[ContextRelatedArticle]:
        if not article.embedding:
            return []

        # We need to perform a pgvector similarity search
        # Filter out the current article; use editorial_status instead of deprecated published_status
        stmt = select(ProcessedArticle).where(
            ProcessedArticle.id != article.id,
        ).order_by(
            ProcessedArticle.embedding.cosine_distance(article.embedding)
        ).limit(limit)

        res = await session.execute(stmt)
        related = res.scalars().all()

        results = []
        for r in related:
            results.append(ContextRelatedArticle(
                id=r.id,
                title=r.title,
                summary=r.summary,
                published_at=r.published_at.isoformat() if r.published_at else None,
                url=r.source_url or r.slug or "",
                similarity_score=0.85  # placeholder
            ))
        return results
