
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ProcessedArticle
from app.schemas.ai_context import ContextCitation


class CitationProvider:
    async def get(self, session: AsyncSession, article: ProcessedArticle) -> list[ContextCitation]:
        citations = []
        # ProcessedArticle uses source_url, not url
        source_url = getattr(article, "source_url", None)
        if source_url:
            citations.append(ContextCitation(
                id="source_url",
                url=source_url,
                title=article.title
            ))
        return citations
