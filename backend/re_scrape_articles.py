import asyncio
import json

from sqlalchemy import select

from agents.ingestion.html_agent import HTMLAgent
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle, RawArticle
from app.services.ingestion.pipeline import compress_content, process_raw_article_to_editorial


async def run():
    async with AsyncSessionLocal() as db:
        # Get raw articles whose processed articles have fallback thumbnails
        stmt = (
            select(RawArticle)
            .join(ProcessedArticle, ProcessedArticle.raw_article_id == RawArticle.id)
            .where(ProcessedArticle.thumbnail_local == '/images/fallback-news.webp')
        )
        res = await db.execute(stmt)
        raw_arts = res.scalars().all()
        print(f"Found {len(raw_arts)} articles with fallback thumbnails to re-scrape")

        agent = HTMLAgent()

        for raw_art in raw_arts:
            print(f"Re-scraping ID {raw_art.id}: {raw_art.title} ({raw_art.url})")

            # Fetch the real HTML using HTMLAgent
            extracted = await agent.extract_article(raw_art.url)
            if not extracted or len(extracted.get("clean_text", "")) < 200:
                print(f"  Extraction failed or clean text too short for {raw_art.id}")
                continue

            print(f"  Successfully extracted HTML ({len(extracted['raw_html'])} bytes) and text ({len(extracted['clean_text'])} words)")

            # Update RawArticle fields
            raw_art.compressed_html = compress_content(extracted["raw_html"])
            raw_art.clean_text = extracted["clean_text"]

            # Reset metadata to non-fallback
            meta = {}
            if raw_art.article_metadata:
                try:
                    meta = json.loads(raw_art.article_metadata)
                except Exception:
                    pass
            meta["rss_fallback"] = False
            meta["extraction_confidence"] = extracted.get("content_score", 95.0)
            raw_art.article_metadata = json.dumps(meta)

            # Get the processed article and clear its thumbnail fields so the pipeline re-runs thumbnail download
            proc_stmt = select(ProcessedArticle).where(ProcessedArticle.raw_article_id == raw_art.id)
            proc_res = await db.execute(proc_stmt)
            proc_art = proc_res.scalars().first()
            if proc_art:
                proc_art.thumbnail_url = None
                proc_art.thumbnail_local = None
                proc_art.thumbnail_hash = None
                proc_art.thumbnail_status = 'pending'

            await db.commit()

            # Re-run pipeline to process this raw article to editorial
            await process_raw_article_to_editorial(db, raw_art.id)
            print(f"  Re-ran pipeline for raw article {raw_art.id}")

        print("Done re-scraping!")

asyncio.run(run())
