from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import correlation_id_ctx
from app.models.article import ArticleReadModel
from app.models.tnt_knowledge import (
    ArticleEntityLink,
    ArticleTopicLink,
    EntityNode,
    RelationshipEdge,
    TimelineEventNode,
    TopicNode,
)
from app.schemas.news import (
    ArticleBase,
    ArticleCard,
    ArticleKnowledgePanel,
    ArticleRelated,
    ArticleResponse,
    KnowledgeEntity,
    KnowledgeRelationship,
    KnowledgeTimelineEvent,
    KnowledgeTopic,
    NavigationInfo,
)
from app.schemas.responses import StandardResponse

router = APIRouter()

@router.get("/{id}", response_model=StandardResponse[ArticleResponse])
async def get_article(id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve full article details, knowledge graph, and semantically related articles.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    # 1. Fetch ArticleReadModel
    stmt = select(ArticleReadModel).where(ArticleReadModel.id == id).where(ArticleReadModel.is_test_data == False)
    # Also support fallback for slug/url matching if id isn't found
    stmt_slug = select(ArticleReadModel).where(ArticleReadModel.url.ilike(f"%{id}%")).where(ArticleReadModel.is_test_data == False)

    result = await db.execute(stmt)
    art = result.scalars().first()
    if not art:
        result = await db.execute(stmt_slug)
        art = result.scalars().first()

    if not art:
        raise HTTPException(status_code=404, detail="Article not found")

    # Fetch clean_html and hero_image from ProcessedArticle if available
    clean_html = art.content
    hero_image = None
    try:
        proc_id = int(art.id)
        from app.models.article import ProcessedArticle
        proc_stmt = select(ProcessedArticle).where(ProcessedArticle.id == proc_id)
        proc_res = await db.execute(proc_stmt)
        proc_art = proc_res.scalars().first()
        if proc_art:
            clean_html = proc_art.clean_html or art.content
            hero_image = proc_art.hero_image
    except Exception:
        pass

    article_base = ArticleBase(
        id=art.id,
        title=art.title,
        url=art.url,
        slug=art.url,
        summary=art.summary,
        source=art.source,
        reading_time=art.reading_time,
        published_at=art.published_at,
        thumbnail_url=art.thumbnail_url,
        thumbnail_local=art.thumbnail_local,
        key_takeaways=art.key_takeaways or None,
        alt_text=getattr(art, "alt_text", None)
    )

    # 2. Build Knowledge Panel
    knowledge = ArticleKnowledgePanel()

    # Entities
    ent_stmt = select(EntityNode, ArticleEntityLink.confidence).join(
        ArticleEntityLink, EntityNode.id == ArticleEntityLink.entity_id
    ).where(ArticleEntityLink.article_id == art.id)
    ent_res = await db.execute(ent_stmt)
    for ent, conf in ent_res.all():
        knowledge.entities.append(KnowledgeEntity(
            id=ent.id, name=ent.canonical_name, type=ent.entity_type, confidence=float(conf or 1.0)
        ))

    # Topics
    top_stmt = select(TopicNode, ArticleTopicLink.confidence).join(
        ArticleTopicLink, TopicNode.name == ArticleTopicLink.topic_name
    ).where(ArticleTopicLink.article_id == art.id)
    top_res = await db.execute(top_stmt)
    for top, conf in top_res.all():
        knowledge.topics.append(KnowledgeTopic(
            name=top.name, confidence=float(conf or 1.0)
        ))

    # Timeline
    time_stmt = select(TimelineEventNode).where(TimelineEventNode.article_id == art.id)
    time_res = await db.execute(time_stmt)
    for t in time_res.scalars().all():
        knowledge.timeline.append(KnowledgeTimelineEvent(
            event_type=t.event_type,
            date=t.date,
            description=t.description,
            entities=t.entities or [],
            confidence=(t.confidence or 1.0)
        ))

    # Relationships
    rel_stmt = select(RelationshipEdge, EntityNode).join(
        EntityNode, RelationshipEdge.target_id == EntityNode.id
    ).where(RelationshipEdge.article_id == art.id)
    rel_res = await db.execute(rel_stmt)
    for rel, tgt in rel_res.all():
        # Also need source name
        src_stmt = select(EntityNode.canonical_name).where(EntityNode.id == rel.source_id)
        src_res = await db.execute(src_stmt)
        src_name = src_res.scalar() or rel.source_id

        knowledge.relationships.append(KnowledgeRelationship(
            source_id=rel.source_id,
            source_name=src_name,
            predicate=rel.predicate,
            target_id=rel.target_id,
            target_name=tgt.canonical_name,
            confidence=float(rel.confidence or 1.0)
        ))

    # 3. Calculate Related Articles using Weighted Semantic Score
    related = ArticleRelated()

    score_sql = text("""
        WITH target_entities AS (
            SELECT entity_id FROM tnt_article_entities WHERE article_id = :art_id
        ),
        target_topics AS (
            SELECT topic_name FROM tnt_article_topics WHERE article_id = :art_id
        ),
        entity_scores AS (
            SELECT article_id, COUNT(*) * 5 as e_score 
            FROM tnt_article_entities 
            WHERE entity_id IN (SELECT entity_id FROM target_entities)
            AND article_id != :art_id
            GROUP BY article_id
        ),
        topic_scores AS (
            SELECT article_id, COUNT(*) * 3 as t_score 
            FROM tnt_article_topics 
            WHERE topic_name IN (SELECT topic_name FROM target_topics)
            AND article_id != :art_id
            GROUP BY article_id
        ),
        combined AS (
            SELECT 
                COALESCE(e.article_id, t.article_id) as rel_article_id,
                COALESCE(e.e_score, 0) + COALESCE(t.t_score, 0) as total_score
            FROM entity_scores e
            FULL OUTER JOIN topic_scores t ON e.article_id = t.article_id
        )
        SELECT rel_article_id, total_score 
        FROM combined 
        WHERE total_score > 0
        ORDER BY total_score DESC 
        LIMIT 5
    """)
    rel_art_res = await db.execute(score_sql, {"art_id": art.id})
    rel_rows = rel_art_res.fetchall()

    for row in rel_rows:
        rel_id = row.rel_article_id
        # fetch article details
        ra_stmt = select(ArticleReadModel).where(ArticleReadModel.id == rel_id).where(ArticleReadModel.is_test_data == False)
        ra = (await db.execute(ra_stmt)).scalars().first()
        if ra:
            related.articles.append(ArticleCard.from_model(ra))

    related.entities = knowledge.entities
    related.topics = knowledge.topics

    # 4. Fetch Ranked IDs from cache or compute
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

    if not ranked_ids:
        from app.editorial.homepage_builder import HomepageBuilder
        global_articles = await HomepageBuilder.build_homepage(db, category_filter=None)
        ranked_ids = [a.id for a in global_articles]

        algo_ver = getattr(settings, "EDITORIAL_ALGORITHM_VERSION", "v1")
        cache_payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "algorithm_version": algo_ver,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "article_ids": ranked_ids
        }
        await redis.set(cache_key, json.dumps(cache_payload), ex=3600)

    position = -1
    navigation = None
    if art.id in ranked_ids:
        position = ranked_ids.index(art.id)
        prev_art = None
        next_art = None

        if position > 0:
            prev_id = ranked_ids[position - 1]
            prev_stmt = select(ArticleReadModel).where(ArticleReadModel.id == prev_id)
            prev_res = await db.execute(prev_stmt)
            prev_model = prev_res.scalars().first()
            if prev_model:
                prev_art = ArticleCard.from_model(prev_model)

        if position < len(ranked_ids) - 1:
            next_id = ranked_ids[position + 1]
            next_stmt = select(ArticleReadModel).where(ArticleReadModel.id == next_id)
            next_res = await db.execute(next_stmt)
            next_model = next_res.scalars().first()
            if next_model:
                next_art = ArticleCard.from_model(next_model)

        navigation = NavigationInfo(
            previous=prev_art,
            next=next_art,
            position=position + 1,
            total=len(ranked_ids)
        )

    # 5. Build Scoring Debug Info
    from app.editorial.freshness import calculate_freshness_multiplier
    now = datetime.now(timezone.utc)
    cutoff_hours = getattr(settings, "EDITORIAL_WINDOW_HOURS", 24)
    decay_model = getattr(settings, "FRESHNESS_DECAY_MODEL", "curved")

    pub_at = art.published_at
    if pub_at and pub_at.tzinfo is None:
        pub_at = pub_at.replace(tzinfo=timezone.utc)

    mult = calculate_freshness_multiplier(pub_at, decay_model=decay_model, window_hours=cutoff_hours, now=now)
    imp_score = float(art.final_score) if art.final_score is not None else 0.0
    eff_score = imp_score * mult

    scoring_debug = {
        "base_impact_score": imp_score,
        "freshness_multiplier": round(mult, 4),
        "effective_score": round(eff_score, 4),
        "decay_model": decay_model,
        "window_hours": cutoff_hours,
        "algorithm_version": getattr(settings, "EDITORIAL_ALGORITHM_VERSION", "v1")
    }

    response_data = ArticleResponse(
        article=article_base,
        content=art.content,
        clean_html=clean_html,
        hero_image=hero_image,
        images=art.images,
        knowledge=knowledge,
        related=related,
        navigation=navigation,
        scoring_debug=scoring_debug
    )

    return StandardResponse(correlation_id=correlation_id, data=response_data)
