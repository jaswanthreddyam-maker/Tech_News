from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import correlation_id_ctx
from app.models.article import ArticleReadModel
from app.models.tnt_knowledge import ArticleEntityLink, ArticleTopicLink, EntityNode, TimelineEventNode, TopicNode
from app.schemas.news import ArticleCard, KnowledgeEntity, KnowledgeTimelineEvent, TopicProfileResponse
from app.schemas.responses import StandardResponse

router = APIRouter()

@router.get("/{slug}", response_model=StandardResponse[TopicProfileResponse])
async def get_topic(slug: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve full topic profile, including trending entities and latest news.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    # 1. Base Topic (Note: slug maps to name here for simplicity, or url decoding)
    topic_name = slug.replace("-", " ").title() if "-" in slug else slug

    stmt = select(TopicNode).where(TopicNode.name.ilike(topic_name))
    top_res = await db.execute(stmt)
    topic = top_res.scalars().first()

    if not topic:
        # We can also dynamically create the view if the topic hasn't been strictly projected but is requested
        topic = TopicNode(name=topic_name, taxonomy_category="Dynamic")

    profile = TopicProfileResponse(
        name=topic.name,
        category=topic.taxonomy_category
    )

    # 2. Latest News
    news_stmt = select(ArticleReadModel).join(
        ArticleTopicLink, ArticleReadModel.id == ArticleTopicLink.article_id
    ).where(ArticleTopicLink.topic_name == topic.name).where(ArticleReadModel.is_test_data == False).order_by(ArticleReadModel.published_at.desc()).limit(10)

    news_res = await db.execute(news_stmt)
    articles = news_res.scalars().all()
    article_ids = [a.id for a in articles]

    for art in articles:
        profile.latest_articles.append(ArticleCard.from_model(art))

    # 3. Trending Entities (Entities mentioned in these articles)
    if article_ids:
        ent_stmt = select(EntityNode, func.count(ArticleEntityLink.article_id).label('mention_count')).join(
            ArticleEntityLink, EntityNode.id == ArticleEntityLink.entity_id
        ).where(ArticleEntityLink.article_id.in_(article_ids)).group_by(EntityNode.id).order_by(func.count(ArticleEntityLink.article_id).desc()).limit(5)

        ent_res = await db.execute(ent_stmt)
        for ent, count in ent_res.all():
            profile.trending_entities.append(KnowledgeEntity(
                id=ent.id, name=ent.canonical_name, type=ent.entity_type, confidence=1.0
            ))

    # 4. Timeline Events (Events in these articles)
    if article_ids:
        time_stmt = select(TimelineEventNode).where(TimelineEventNode.article_id.in_(article_ids)).order_by(TimelineEventNode.date.desc()).limit(5)
        time_res = await db.execute(time_stmt)
        for t in time_res.scalars().all():
            profile.timeline.append(KnowledgeTimelineEvent(
                event_type=t.event_type, date=t.date, description=t.description,
                entities=t.entities or [], confidence=(t.confidence or 1.0)
            ))

    return StandardResponse(correlation_id=correlation_id, data=profile)
