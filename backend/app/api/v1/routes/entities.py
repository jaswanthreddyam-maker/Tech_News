from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import correlation_id_ctx
from app.models.article import ArticleReadModel
from app.models.tnt_knowledge import ArticleEntityLink, EntityNode, RelationshipEdge, TimelineEventNode
from app.schemas.news import (
    ArticleCard,
    EntityProfileResponse,
    EntityStats,
    KnowledgeEntity,
    KnowledgeRelationship,
    KnowledgeTimelineEvent,
)
from app.schemas.responses import StandardResponse

router = APIRouter()

@router.get("/{id}", response_model=StandardResponse[EntityProfileResponse])
async def get_entity(id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve full entity profile, including timeline, relationships, and latest news.
    """
    correlation_id = correlation_id_ctx.get() or "system"

    # 1. Base Entity
    stmt = select(EntityNode).where(EntityNode.id == id)
    ent_res = await db.execute(stmt)
    ent = ent_res.scalars().first()

    if not ent:
        raise HTTPException(status_code=404, detail="Entity not found")

    # 2. Stats
    count_stmt = select(func.count(ArticleEntityLink.article_id)).where(ArticleEntityLink.entity_id == id)
    count = (await db.execute(count_stmt)).scalar() or 0

    stats = EntityStats(
        mention_count=count,
        first_seen=ent.first_seen,
        last_seen=ent.last_seen
    )

    profile = EntityProfileResponse(
        id=ent.id,
        name=ent.canonical_name,
        type=ent.entity_type,
        description=ent.description,
        aliases=ent.aliases or [],
        stats=stats
    )

    # 3. Latest News
    news_stmt = select(ArticleReadModel).join(
        ArticleEntityLink, ArticleReadModel.id == ArticleEntityLink.article_id
    ).where(ArticleEntityLink.entity_id == id).where(ArticleReadModel.is_test_data == False).order_by(ArticleReadModel.published_at.desc()).limit(5)

    news_res = await db.execute(news_stmt)
    for art in news_res.scalars().all():
        profile.latest_news.append(ArticleCard.from_model(art))

    # 4. Timeline Events
    # Currently timeline events store entities as a list of strings, so we check if id is in array
    time_stmt = select(TimelineEventNode).where(TimelineEventNode.entities.contains([id])).order_by(TimelineEventNode.date.desc()).limit(10)
    time_res = await db.execute(time_stmt)
    for t in time_res.scalars().all():
        profile.timeline.append(KnowledgeTimelineEvent(
            event_type=t.event_type, date=t.date, description=t.description,
            entities=t.entities or [], confidence=(t.confidence or 1.0)
        ))

    # 5. Relationships & Neighbors
    rel_stmt = select(RelationshipEdge).where(
        or_(RelationshipEdge.source_id == id, RelationshipEdge.target_id == id)
    )
    rel_res = await db.execute(rel_stmt)
    edges = rel_res.scalars().all()

    neighbor_ids = set()
    for edge in edges:
        other_id = edge.target_id if edge.source_id == id else edge.source_id
        neighbor_ids.add(other_id)

    # Resolve names for relationships
    if edges or neighbor_ids:
        # Load all neighbor nodes
        neighbors_stmt = select(EntityNode).where(EntityNode.id.in_(list(neighbor_ids)))
        neighbors_res = await db.execute(neighbors_stmt)
        neighbors_map = {n.id: n for n in neighbors_res.scalars().all()}

        for edge in edges:
            src_name = ent.canonical_name if edge.source_id == id else neighbors_map.get(edge.source_id, EntityNode(canonical_name=edge.source_id)).canonical_name
            tgt_name = ent.canonical_name if edge.target_id == id else neighbors_map.get(edge.target_id, EntityNode(canonical_name=edge.target_id)).canonical_name

            profile.relationships.append(KnowledgeRelationship(
                source_id=edge.source_id, source_name=src_name,
                predicate=edge.predicate,
                target_id=edge.target_id, target_name=tgt_name,
                confidence=(edge.confidence or 1.0)
            ))

        # Add to Related Companies (assuming we just return neighbors of type COMPANY or any)
        for n_id, n_obj in neighbors_map.items():
            if n_obj.entity_type == "COMPANY":
                profile.related_companies.append(KnowledgeEntity(
                    id=n_obj.id, name=n_obj.canonical_name, type=n_obj.entity_type, confidence=1.0
                ))

    return StandardResponse(correlation_id=correlation_id, data=profile)
