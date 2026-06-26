
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import correlation_id_ctx
from app.models.article import ArticleReadModel
from app.models.tnt_knowledge import EntityNode, TopicNode
from app.schemas.news import SearchResultItem
from app.schemas.responses import StandardResponse

router = APIRouter()

@router.get("", response_model=StandardResponse[list[SearchResultItem]])
async def search_all(
    q: str | None = Query(None, description="Keywords to query"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Search articles, entities, and topics.
    """
    correlation_id = correlation_id_ctx.get() or "system"
    results = []

    if not q or not q.strip():
        return StandardResponse(correlation_id=correlation_id, data=[])

    term = f"%{q.strip().lower()}%"

    # 1. Search Entities
    ent_stmt = select(EntityNode).where(
        or_(
            EntityNode.canonical_name.ilike(term),
            EntityNode.description.ilike(term)
        )
    ).limit(5)
    ent_res = await db.execute(ent_stmt)
    for ent in ent_res.scalars().all():
        results.append(SearchResultItem(
            type="entity",
            id=ent.id,
            title=ent.canonical_name,
            description=ent.description
        ))

    # 2. Search Topics
    top_stmt = select(TopicNode).where(TopicNode.name.ilike(term)).limit(5)
    top_res = await db.execute(top_stmt)
    for top in top_res.scalars().all():
        results.append(SearchResultItem(
            type="topic",
            id=top.name,
            title=top.name,
            description=f"Category: {top.taxonomy_category}"
        ))

    # 3. Search Articles
    art_stmt = select(ArticleReadModel).where(
        or_(
            ArticleReadModel.title.ilike(term),
            ArticleReadModel.summary.ilike(term)
        ),
        ArticleReadModel.is_test_data == False
    ).order_by(desc(ArticleReadModel.published_at)).limit(limit)
    art_res = await db.execute(art_stmt)
    for art in art_res.scalars().all():
        results.append(SearchResultItem(
            type="article",
            id=art.id,
            title=art.title,
            description=art.summary,
            url=art.url,
            date=art.published_at
        ))

    return StandardResponse(correlation_id=correlation_id, data=results)
