"""
PersistenceService — Transactional Writes & Outbox Event Dispatcher.
Manages transactional raw & processed article writes and publishes event outbox envelopes.
"""

import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.article import RawArticle, ProcessedArticle
from app.core.event_bus import publish_event

logger = logging.getLogger("tech_news.persistence_service")


class PersistenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_raw_article(
        self,
        source_id: int,
        title: str,
        url: str,
        url_hash: str,
        title_hash: str,
        compressed_html: Optional[bytes],
        clean_text: str,
        metadata_dict: Dict[str, Any],
        status: str = "scraped",
        filter_reason: Optional[str] = None,
        pipeline_version: str = "1.0.0",
        parser_version: str = "1.0.0",
    ) -> RawArticle:
        from sqlalchemy import select
        existing_stmt = select(RawArticle).where(
            RawArticle.url_hash == url_hash,
            RawArticle.title_hash == title_hash
        )
        existing_res = await self.db.execute(existing_stmt)
        existing_raw = existing_res.scalars().first()
        if existing_raw:
            return existing_raw

        raw_article = RawArticle(
            source_id=source_id,
            title=title,
            url=url,
            url_hash=url_hash,
            title_hash=title_hash,
            compressed_html=compressed_html,
            clean_text=clean_text,
            article_metadata=json.dumps(metadata_dict),
            status=status,
            filter_reason=filter_reason,
            parser_version=parser_version,
        )
        self.db.add(raw_article)
        await self.db.flush()
        await publish_event(
            "INGESTION-PIPELINE",
            f"RawArticle saved (ID: {raw_article.id}): '{title[:40]}'",
            "info",
        )
        return raw_article

    async def save_processed_article(self, proc_art: ProcessedArticle) -> ProcessedArticle:
        self.db.add(proc_art)
        await self.db.flush()
        await publish_event(
            "PROCESSOR-PIPELINE",
            f"ProcessedArticle saved (ID: {proc_art.id}, Slug: '{proc_art.slug[:30]}')",
            "info",
        )
        return proc_art
