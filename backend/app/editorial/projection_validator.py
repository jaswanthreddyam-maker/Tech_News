import logging
import json
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ArticleReadModel
from app.models.projection import HomepageProjection, CategoryDeskProjection
from app.core.redis import get_redis_client

logger = logging.getLogger("tech_news.editorial.projection_validator")


from sqlalchemy import cast, String, or_, and_
from datetime import datetime, timezone
from app.models.article import ProcessedArticle


async def _get_active_article_ids(db: AsyncSession, ref_ids: List[str]) -> set[str]:
    if not ref_ids:
        return set()
    now = datetime.now(timezone.utc)
    stmt = (
        select(ArticleReadModel.id)
        .outerjoin(ProcessedArticle, cast(ProcessedArticle.id, String) == ArticleReadModel.id)
        .where(
            and_(
                ArticleReadModel.id.in_(ref_ids),
                ArticleReadModel.is_test_data == False,
                ArticleReadModel.publication_status == "PUBLISHED",
                or_(ProcessedArticle.is_archived == None, ProcessedArticle.is_archived == False),
                or_(ProcessedArticle.is_expired == None, ProcessedArticle.is_expired == False),
                or_(ProcessedArticle.expires_at == None, ProcessedArticle.expires_at > now),
            )
        )
    )
    res = await db.execute(stmt)
    return set(str(art_id) for art_id in res.scalars().all())


def determine_status(referenced_count: int, existing_count: int) -> str:
    if referenced_count == 0:
        return "EMPTY"
    if existing_count == referenced_count:
        return "VALID"
    if existing_count == 0:
        return "FULLY_STALE"
    return "PARTIALLY_STALE"


async def validate_editorial_projections_integrity(db: AsyncSession) -> Dict[str, Any]:
    """
    Read-only diagnostic utility to inspect and validate the integrity of 
    HomepageProjections, CategoryDeskProjections, and Redis ranking cache against ArticleReadModel.
    """
    report: Dict[str, Any] = {
        "homepage_projection": {},
        "category_desk_projections": {},
        "redis_ranking_cache": {},
        "summary_status": "VALID"
    }

    # 1. Inspect HomepageProjection
    hp_stmt = select(HomepageProjection).order_by(HomepageProjection.created_at.desc()).limit(1)
    hp_res = await db.execute(hp_stmt)
    latest_hp = hp_res.scalars().first()

    if latest_hp and latest_hp.stories_json:
        hp_ref_ids = [str(s["id"]) for s in latest_hp.stories_json if "id" in s]
        unique_ref_ids = list(dict.fromkeys(hp_ref_ids))
        
        existing_ids = await _get_active_article_ids(db, unique_ref_ids)
        missing_ids = [aid for aid in unique_ref_ids if aid not in existing_ids]
        hp_status = determine_status(len(unique_ref_ids), len(existing_ids))
        
        report["homepage_projection"] = {
            "projection_id": str(latest_hp.id),
            "projection_version": latest_hp.projection_version,
            "created_at": latest_hp.created_at.isoformat() if latest_hp.created_at else None,
            "referenced_count": len(unique_ref_ids),
            "existing_count": len(existing_ids),
            "missing_count": len(missing_ids),
            "missing_ids": missing_ids,
            "has_duplicates": len(hp_ref_ids) != len(unique_ref_ids),
            "status": hp_status
        }
    else:
        report["homepage_projection"] = {
            "referenced_count": 0,
            "existing_count": 0,
            "missing_count": 0,
            "missing_ids": [],
            "status": "EMPTY"
        }

    # 2. Inspect CategoryDeskProjections
    cd_stmt = select(CategoryDeskProjection)
    cd_res = await db.execute(cd_stmt)
    desks = cd_res.scalars().all()

    desks_report = {}
    cd_overall_status = "VALID" if desks else "EMPTY"
    
    for desk in desks:
        ref_ids = [str(aid) for aid in (desk.article_ids or [])]
        unique_ids = list(dict.fromkeys(ref_ids))
        
        if unique_ids:
            existing_ids = await _get_active_article_ids(db, unique_ids)
            missing_ids = [aid for aid in unique_ids if aid not in existing_ids]
            desk_status = determine_status(len(unique_ids), len(existing_ids))
        else:
            existing_ids = set()
            missing_ids = []
            desk_status = "EMPTY"

        desks_report[desk.category_slug] = {
            "referenced_count": len(unique_ids),
            "existing_count": len(existing_ids),
            "missing_count": len(missing_ids),
            "missing_ids": missing_ids,
            "status": desk_status
        }

        if desk_status in ("PARTIALLY_STALE", "FULLY_STALE"):
            cd_overall_status = "PARTIALLY_STALE"

    report["category_desk_projections"] = {
        "desks": desks_report,
        "overall_status": cd_overall_status
    }

    # 3. Inspect Redis Ranking Cache
    redis_status = "EMPTY"
    redis_ref_ids: List[str] = []
    redis_missing_ids: List[str] = []
    try:
        redis = get_redis_client()
        if redis:
            cached = await redis.get("editorial:v1:homepage_ranked_ids")
            if cached:
                cache_data = json.loads(cached)
                raw_ids = cache_data.get("article_ids", [])
                redis_ref_ids = [str(aid) for aid in raw_ids]
                unique_redis_ids = list(dict.fromkeys(redis_ref_ids))
                
                if unique_redis_ids:
                    existing_ids = await _get_active_article_ids(db, unique_redis_ids)
                    redis_missing_ids = [aid for aid in unique_redis_ids if aid not in existing_ids]
                    redis_status = determine_status(len(unique_redis_ids), len(existing_ids))
    except Exception as e:
        logger.warning(f"Failed to inspect Redis ranking cache: {e}")

    report["redis_ranking_cache"] = {
        "referenced_count": len(redis_ref_ids),
        "missing_count": len(redis_missing_ids),
        "missing_ids": redis_missing_ids,
        "status": redis_status
    }

    # Overall summary status
    statuses = [
        report["homepage_projection"]["status"],
        report["category_desk_projections"]["overall_status"],
        report["redis_ranking_cache"]["status"]
    ]
    if "FULLY_STALE" in statuses:
        report["summary_status"] = "FULLY_STALE"
    elif "PARTIALLY_STALE" in statuses:
        report["summary_status"] = "PARTIALLY_STALE"
    elif all(s == "VALID" for s in statuses):
        report["summary_status"] = "VALID"
    else:
        report["summary_status"] = "INCOMPLETE"

    return report
