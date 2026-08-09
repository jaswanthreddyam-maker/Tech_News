import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle, ProcessedArticle
from app.services.ingestion.image_helper import extract_all_candidate_urls

async def inspect_candidates():
    openai_ids = [86, 82, 87, 88, 89, 91]
    async with AsyncSessionLocal() as db:
        for aid in openai_ids:
            proc = (await db.execute(select(ProcessedArticle).where(ProcessedArticle.id == aid))).scalars().first()
            if not proc:
                continue
            raw = (await db.execute(select(RawArticle).where(RawArticle.id == proc.raw_article_id))).scalars().first() if proc.raw_article_id else None
            
            from app.services.ingestion.pipeline import decompress_html
            raw_html = decompress_html(raw.compressed_html) if (raw and raw.compressed_html) else ""
            candidates = extract_all_candidate_urls(raw_html, raw.url if raw else proc.slug) if raw_html else []
            
            print(f"\n==========================================")
            print(f"Article ID {aid}: {proc.title}")
            print(f"Stored thumbnail_url: {proc.thumbnail_url}")
            print(f"Stored thumbnail_source: {proc.thumbnail_source}")
            print(f"Total Candidates Extracted: {len(candidates)}")
            for idx, c in enumerate(candidates):
                print(f"  [{idx+1}] Source: {c.get('source')}, Score: {c.get('score')} -> URL: {c.get('url')[:90]}")

if __name__ == "__main__":
    asyncio.run(inspect_candidates())
