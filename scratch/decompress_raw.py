import asyncio
import zlib
from sqlalchemy import select
from app.core.database import async_engine, AsyncSessionLocal
from app.models.article import RawArticle
from app.models.source import Source

async def main():
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(RawArticle).where(RawArticle.id == 1576))
        art = res.scalar()
        if art and art.compressed_html:
            decompressed = zlib.decompress(art.compressed_html).decode('utf-8', errors='replace')
            print("Decompressed HTML Length:", len(decompressed))
            print("Decompressed HTML Content:")
            print(decompressed[:1000])
        else:
            print("Article or compressed HTML not found.")

if __name__ == "__main__":
    asyncio.run(main())
