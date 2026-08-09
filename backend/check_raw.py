import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle
from app.services.ingestion.processor import decompress_html

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(RawArticle).order_by(RawArticle.id.desc()).limit(1))
        ra = res.scalars().first()
        html = decompress_html(ra.compressed_html) if ra.compressed_html else ''
        print(f"LEN: {len(html)}")
        print(f"TEXT: {html[:300]}")

if __name__ == "__main__":
    asyncio.run(run())
