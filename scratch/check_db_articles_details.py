import asyncio
from sqlalchemy import text
from app.core.database import async_engine

async def main():
    async with async_engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT id, title, url, source, published_at, projected_at 
            FROM articles 
            ORDER BY projected_at DESC
            LIMIT 10;
        """))
        rows = res.fetchall()
        print("Articles (Read Model) rows:")
        for r in rows:
            mapped = dict(r._mapping)
            # Safe print for Windows terminal encoding
            safe_title = mapped["title"].encode("ascii", "replace").decode("ascii")
            print(f"ID: {mapped['id']}, Title: {safe_title}, PublishedAt: {mapped['published_at']}, ProjectedAt: {mapped['projected_at']}")

if __name__ == "__main__":
    asyncio.run(main())
