import logging
import math
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ProcessedArticle
from app.models.source import Source

logger = logging.getLogger("tech_news.trends")

# 18-hour half-life decay constant (lambda = ln(2) / 18)
DECAY_CONSTANT_HOURLY = math.log(2) / 18.0

# Source category trust weights
SOURCE_TRUST_WEIGHTS = {"official": 1.8, "editorial": 1.4, "community": 1.0, "social": 0.7}


async def calculate_latest_trends(db: AsyncSession) -> dict:
    """
    Dynamic mathematical Trend Scoring Engine with:
    1. Source-trust authority weighting.
    2. 18-hour exponential freshness decay.
    3. Cross-source diversity multi-boost (beta=0.5 per additional source).
    4. Anti-spam protections (enforcing maximum of 3 articles per source per tag).
    """
    logger.info("Trend Engine: Computing authority-weighted dynamic trends...")

    current_time = datetime.now(timezone.utc)
    # 1. Fetch all processed articles from the past 7 days with their source config
    stmt = (
        select(ProcessedArticle, Source)
        .outerjoin(Source, ProcessedArticle.source_id == Source.id)
        .where(
            and_(
                ProcessedArticle.published_status == "published",
                ProcessedArticle.is_archived == False,
                or_(ProcessedArticle.expires_at == None, ProcessedArticle.expires_at > current_time),
            )
        )
        .order_by(ProcessedArticle.published_at.desc())
    )
    res = await db.execute(stmt)
    rows = res.all()

    if not rows:
        logger.info("Trend Engine: No published articles found in database.")
        return {"status": "success", "trends_computed": 0}

    current_time = datetime.now(timezone.utc)
    tag_data = {}  # tag -> list of {article, source_category, hours_elapsed, source_id}

    # 2. Tokenize tags and group article data
    for proc_art, source_obj in rows:
        tags = []
        if getattr(proc_art, "primary_topics", None):
            if isinstance(proc_art.primary_topics, list):
                tags.extend([str(t).strip().lower() for t in proc_art.primary_topics if str(t).strip()])
            elif isinstance(proc_art.primary_topics, str):
                tags.extend([t.strip().lower() for t in proc_art.primary_topics.split(",") if t.strip()])
        if not tags and getattr(proc_art, "seo_keywords", None):
            tags.extend([k.strip().lower() for k in proc_art.seo_keywords.split(",") if k.strip()])
        if not tags and getattr(proc_art, "tags", None):
            if isinstance(proc_art.tags, list):
                tags.extend([str(t).strip().lower() for t in proc_art.tags if str(t).strip()])
            elif isinstance(proc_art.tags, str):
                tags.extend([t.strip().lower() for t in proc_art.tags.split(",") if t.strip()])

        if not tags:
            continue

        source_category = source_obj.category if source_obj else "community"
        source_id = source_obj.id if source_obj else -1

        # Calculate time elapsed in hours
        published_at = proc_art.published_at
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=timezone.utc)
        hours_elapsed = (current_time - published_at).total_seconds() / 3600.0

        for tag in tags:
            if tag not in tag_data:
                tag_data[tag] = []
            tag_data[tag].append({"source_id": source_id, "category": source_category, "hours_elapsed": hours_elapsed})

    # 3. Calculate scores with time decay, source trust, caps, and diversity boosts
    computed_trends = []

    for tag, occurrences in tag_data.items():
        # A. Group occurrences by source to apply spam protection caps
        source_groups = {}
        for occ in occurrences:
            src_id = occ["source_id"]
            if src_id not in source_groups:
                source_groups[src_id] = []
            source_groups[src_id].append(occ)

        decay_weighted_sum = 0.0
        distinct_sources = set()

        for src_id, occ_list in source_groups.items():
            if src_id != -1:
                distinct_sources.add(src_id)

            # Apply Source Spam Shield Cap: max 3 contributions per source
            # Sort by hours_elapsed to prioritize the freshest ones
            occ_list.sort(key=lambda x: x["hours_elapsed"])
            capped_list = occ_list[:3]

            for occ in capped_list:
                trust_multiplier = SOURCE_TRUST_WEIGHTS.get(occ["category"], 1.0)
                # Exponential decay: e^(-lambda * t)
                time_decay = math.exp(-DECAY_CONSTANT_HOURLY * occ["hours_elapsed"])
                decay_weighted_sum += trust_multiplier * time_decay

        num_sources = len(distinct_sources)
        if num_sources == 0:
            num_sources = 1

        # B. Apply Cross-Source Diversity Boost
        # 1.0 + 0.5 * (N - 1)
        diversity_bonus = 1.0 + 0.5 * (num_sources - 1)
        final_score = round(decay_weighted_sum * diversity_bonus, 2)

        if final_score > 0.05:
            computed_trends.append((tag, final_score))

    # 4. Sort and select top 8 trends
    computed_trends.sort(key=lambda x: x[1], reverse=True)
    top_trends = computed_trends[:8]

    # 5. Atomic write-replacement to trending_topics table
    try:
        # Clear existing trending topics
        await db.execute(text("DELETE FROM trending_topics"))

        # Insert new trending topics
        for tag, score in top_trends:
            # We scale weight up to integer mapping (rounded score * 10)
            weight = max(1, int(score * 10))
            await db.execute(
                text("INSERT INTO trending_topics (topic, weight, updated_at) VALUES (:topic, :weight, NOW())"),
                {"topic": tag, "weight": weight},
            )
        await db.commit()
        logger.info(f"Trend Engine: Successfully updated trending_topics. Top trends: {top_trends}")
    except Exception as e:
        if "trending_topics" in str(e):
            try:
                await db.rollback()
                await db.execute(text("""
                    CREATE TABLE IF NOT EXISTS trending_topics (
                        id SERIAL PRIMARY KEY,
                        topic VARCHAR(255) UNIQUE NOT NULL,
                        weight INTEGER DEFAULT 1,
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """))
                await db.execute(text("DELETE FROM trending_topics"))
                for tag, score in top_trends:
                    weight = max(1, int(score * 10))
                    await db.execute(
                        text("INSERT INTO trending_topics (topic, weight, updated_at) VALUES (:topic, :weight, NOW())"),
                        {"topic": tag, "weight": weight},
                    )
                await db.commit()
                logger.info(f"Trend Engine: Created trending_topics table and updated trends: {top_trends}")
            except Exception as inner_e:
                await db.rollback()
                logger.error(f"Trend Engine: Failed to update database trending topics: {inner_e!s}", exc_info=True)
        else:
            await db.rollback()
            logger.error(f"Trend Engine: Failed to update database trending topics: {e!s}", exc_info=True)

    return {"status": "success", "trends_computed": len(top_trends), "top": top_trends}
