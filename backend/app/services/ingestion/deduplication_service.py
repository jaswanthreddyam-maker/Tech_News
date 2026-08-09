"""
DeduplicationService — Enterprise Unified Deduplication Engine.
Single source of truth for composite MD5 hard deduplication and PostgreSQL pg_trgm trigram soft deduplication.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.article import RawArticle
from app.services.ingestion.utils import get_hash, normalize_url

logger = logging.getLogger("tech_news.deduplication")


class DeduplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.dedup_threshold = getattr(settings, "DEDUP_THRESHOLD", 0.75)

    async def check_duplicate(
        self, raw_title: str, raw_url: str, current_time: Optional[datetime] = None
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Check whether an incoming article is a duplicate using hard MD5 hashing and SQL pg_trgm trigram search.
        
        Returns:
            Tuple[is_duplicate (bool), reason (str), matched_article_id (Optional[int])]
        """
        if not current_time:
            current_time = datetime.now(timezone.utc)

        normalized_url = normalize_url(raw_url)
        url_hash = get_hash(normalized_url)
        title_hash = get_hash(raw_title)

        # 1. Hard Deduplication: Exact URL hash + Title hash match
        dup_stmt = select(RawArticle).where(
            (RawArticle.url_hash == url_hash) & (RawArticle.title_hash == title_hash)
        )
        dup_res = await self.db.execute(dup_stmt)
        existing_article = dup_res.scalars().first()

        if existing_article:
            needs_refresh = False
            if existing_article.article_metadata:
                try:
                    import json
                    meta = json.loads(existing_article.article_metadata)
                    needs_refresh = meta.get("needs_html_refresh", False)
                    if needs_refresh:
                        next_retry_str = meta.get("next_retry_after")
                        if next_retry_str:
                            next_retry = datetime.fromisoformat(next_retry_str)
                            if current_time < next_retry:
                                needs_refresh = False
                except Exception:
                    pass

            if existing_article.status in ("failed", "discovered") or needs_refresh:
                logger.info(f"DeduplicationService: Re-triggering failed/queued/degraded article: '{raw_title}' (ID: {existing_article.id})")
                return False, "retry_failed", existing_article.id
            else:
                logger.info(f"DeduplicationService: Hard duplicate match for: '{raw_title}' (ID: {existing_article.id})")
                return True, "hard_url_title_hash_match", existing_article.id

        # 2. Soft Deduplication: Sub-5ms PostgreSQL pg_trgm GIN Trigram Similarity Query
        yesterday = current_time - timedelta(days=1)
        trgm_stmt = text(
            "SELECT id, title, similarity(title, :raw_title) AS sim FROM raw_articles "
            "WHERE scraped_at >= :yesterday AND status != 'deduplicated' "
            "AND similarity(title, :raw_title) >= :threshold "
            "ORDER BY similarity(title, :raw_title) DESC LIMIT 1;"
        )
        trgm_res = await self.db.execute(
            trgm_stmt,
            {
                "yesterday": yesterday,
                "raw_title": raw_title,
                "threshold": self.dedup_threshold,
            },
        )
        matching_row = trgm_res.first()

        if matching_row:
            matched_id, matched_title, sim_score = matching_row[0], matching_row[1], matching_row[2]
            logger.info(
                f"DeduplicationService: SQL pg_trgm soft duplicate match (similarity: {sim_score:.2f}) "
                f"for '{raw_title}' -> Matches ID {matched_id} ('{matched_title[:40]}...')"
            )
            return True, f"soft_trigram_similarity_match ({sim_score:.2f})", matched_id

        return False, "unique", None
