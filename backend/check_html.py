import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle
from app.services.ingestion.processor import decompress_html
from app.services.ingestion.image_helper import extract_all_candidate_urls

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(RawArticle).order_by(RawArticle.id.desc()).limit(1)
        )
        art = res.scalars().first()
        html = decompress_html(art.compressed_html) if art.compressed_html else ""
        print(f"URL: {art.url}")
        print(f"HTML len: {len(html)}")
        cands = extract_all_candidate_urls(html, art.url)
        print(f"Candidates: {cands}")
        if len(html) > 500:
            print(f"Preview: {html[:500]}")

if __name__ == "__main__":
    asyncio.run(run())
