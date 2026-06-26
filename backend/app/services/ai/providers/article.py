from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ProcessedArticle
from app.schemas.ai_context import ContextArticle


class ArticleProvider:
    async def get(self, session: AsyncSession, article_id: int) -> ContextArticle:
        # Eagerly load category to avoid lazy-loading in async context
        stmt = (
            select(ProcessedArticle)
            .options(selectinload(ProcessedArticle.category))
            .where(ProcessedArticle.id == article_id)
        )
        res = await session.execute(stmt)
        article = res.scalar_one_or_none()
        if not article:
            raise ValueError(f"Article {article_id} not found")

        # ProcessedArticle doesn't have a direct 'entities' field; use empty list
        entities = getattr(article, "entities", None) or []

        return ContextArticle(
            id=article.id,
            title=article.title,
            slug=article.slug,
            content=article.content,
            summary=article.summary,
            published_at=article.published_at.isoformat() if article.published_at else None,
            source_name=article.source_name,
            category=article.category.name if article.category else None,
            entities=entities
        )
