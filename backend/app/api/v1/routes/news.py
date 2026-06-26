
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import correlation_id_ctx
from app.models.article import ArticleReadModel
from app.models.tnt_knowledge import ArticleEntityLink, ArticleTopicLink, EntityNode
from app.schemas.news import ArticleCard
from app.schemas.responses import PaginatedResponse, PaginationMetadata

router = APIRouter()

@router.get("", response_model=PaginatedResponse[ArticleCard])
async def list_articles(
    category: str | None = Query(None, description="Topic filter slug"),
    cursor: str | None = Query(None, description="Cursor for pagination"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch articles from ArticleReadModel using the versioned Redis ranking cache.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    from app.core.redis import get_redis_client
    from app.core.config import settings
    from datetime import datetime, timezone, timedelta
    import json

    redis = get_redis_client()
    cache_key = "editorial:v1:homepage_ranked_ids"
    cached = await redis.get(cache_key)

    ranked_ids = []
    if cached:
        try:
            cache_data = json.loads(cached)
            ranked_ids = cache_data.get("article_ids", [])
        except Exception:
            pass

    articles = []
    if ranked_ids:
        stmt = select(ArticleReadModel).where(ArticleReadModel.id.in_(ranked_ids))
        res = await db.execute(stmt)
        articles_map = {art.id: art for art in res.scalars().all()}
        # Maintain precise ranking order
        articles = [articles_map[aid] for aid in ranked_ids if aid in articles_map]
    else:
        from app.editorial.homepage_builder import HomepageBuilder
        global_articles = await HomepageBuilder.build_homepage(db, category_filter=None)
        articles = global_articles
        ranked_ids = [a.id for a in global_articles]

        algo_ver = getattr(settings, "EDITORIAL_ALGORITHM_VERSION", "v1")
        cache_payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "algorithm_version": algo_ver,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "article_ids": ranked_ids
        }
        await redis.set(cache_key, json.dumps(cache_payload), ex=3600)

    # If category filter is active, filter from the global ranked articles
    if category:
        category_lower = category.lower().strip()
        filtered_articles = []
        for art in articles:
            topic_stmt = select(ArticleTopicLink.topic_name).where(ArticleTopicLink.article_id == art.id)
            topic_res = await db.execute(topic_stmt)
            topics = topic_res.scalars().all()
            if any(category_lower in t.lower() for t in topics):
                filtered_articles.append(art)
        articles = filtered_articles

    # Paginate by slicing
    articles = articles[:limit]

    articles_list = []
    for art in articles:
        # Fetch topics for the card
        topic_stmt = select(ArticleTopicLink.topic_name).where(ArticleTopicLink.article_id == art.id)
        topic_res = await db.execute(topic_stmt)
        topics = topic_res.scalars().all()

        # Fetch entities for the card
        entity_stmt = select(EntityNode.canonical_name).join(
            ArticleEntityLink, EntityNode.id == ArticleEntityLink.entity_id
        ).where(ArticleEntityLink.article_id == art.id).limit(3)
        entity_res = await db.execute(entity_stmt)
        entities = entity_res.scalars().all()

        articles_list.append(ArticleCard.from_model(
            art,
            topics=topics,
            entities=entities
        ))

    return PaginatedResponse(
        correlation_id=correlation_id,
        data=articles_list,
        pagination=PaginationMetadata(next_cursor=None, has_more=False, limit=limit),
    )

import html
from datetime import datetime, timezone

from fastapi import Response


@router.get("/rss.xml")
async def get_rss(db: AsyncSession = Depends(get_db)):
    """
    Generate an RSS 2.0 feed from the canonical ArticleReadModel.
    """
    stmt = select(ArticleReadModel).where(ArticleReadModel.is_test_data == False).order_by(desc(ArticleReadModel.published_at)).limit(20)
    result = await db.execute(stmt)
    articles = result.scalars().all()

    pub_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")

    items = []
    for art in articles:
        link = art.url or f"https://technewstoday.com/articles/{art.id}"
        desc_escaped = html.escape(art.summary or "")
        title_escaped = html.escape(art.title or "")
        art_pub = art.published_at.strftime("%a, %d %b %Y %H:%M:%S %z") if art.published_at else pub_date

        item = f"""
        <item>
            <title>{title_escaped}</title>
            <link>{link}</link>
            <description>{desc_escaped}</description>
            <pubDate>{art_pub}</pubDate>
            <guid>{link}</guid>
        </item>
        """
        items.append(item)

    items_xml = "".join(items)

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
    <title>Tech News Today</title>
    <link>https://technewstoday.com</link>
    <description>The latest technology news, powered by AI.</description>
    <language>en-us</language>
    <pubDate>{pub_date}</pubDate>
    <lastBuildDate>{pub_date}</lastBuildDate>
    {items_xml}
</channel>
</rss>
"""
    return Response(content=rss_xml.strip(), media_type="application/xml")
