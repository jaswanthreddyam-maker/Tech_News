"""
Reprocess all article HTML content using the new 15-point DOM sanitizer.
"""

import asyncio
import re
import zlib
from bs4 import BeautifulSoup
from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel, ProcessedArticle, RawArticle
from app.services.ingestion.processor import (
    calculate_reading_time,
    clean_and_sanitize_html,
)


def decompress_html(compressed_payload: bytes) -> str:
    if not compressed_payload:
        return ""
    try:
        return zlib.decompress(compressed_payload).decode("utf-8", errors="ignore")
    except Exception:
        return ""


async def run() -> None:
    async with AsyncSessionLocal() as session:
        # Fetch all processed articles
        stmt = select(ProcessedArticle, RawArticle).outerjoin(
            RawArticle, ProcessedArticle.raw_article_id == RawArticle.id
        )
        rows = (await session.execute(stmt)).all()

        print(f"\nReprocessing {len(rows)} articles with 15-Point DOM Sanitizer...")

        updated_count = 0
        for processed, raw in rows:
            raw_html = decompress_html(raw.compressed_html) if raw and raw.compressed_html else ""
            if not raw_html:
                raw_html = processed.clean_html or processed.content or ""

            if not raw_html:
                continue

            cleaned_html = clean_and_sanitize_html(raw_html)

            # Strip HTML tags to produce clean plain text content
            soup = BeautifulSoup(cleaned_html, "html.parser")
            plain_text = soup.get_text(separator="\n\n", strip=True)

            reading_time = calculate_reading_time(plain_text)

            # Update ProcessedArticle
            processed.clean_html = cleaned_html
            processed.content = plain_text
            processed.reading_time_minutes = reading_time

            # Update ArticleReadModel
            await session.execute(
                update(ArticleReadModel)
                .where(ArticleReadModel.slug == processed.slug)
                .values(content=plain_text, reading_time=reading_time)
            )

            updated_count += 1
            print(f"  [OK] Updated Article ID {processed.id}: {processed.title[:50]}...")

        await session.commit()
        print(f"\nSuccessfully reprocessed {updated_count} articles cleanly!\n")


if __name__ == "__main__":
    asyncio.run(run())
