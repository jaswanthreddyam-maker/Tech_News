import asyncio
from sqlalchemy import text
from app.core.database import async_engine

async def main():
    async with async_engine.connect() as conn:
        # Check articles count
        count_res = await conn.execute(text("SELECT count(*) FROM articles;"))
        count = count_res.scalar()
        print("Total rows in articles read model:", count)
        
        # Check processed articles count
        proc_count_res = await conn.execute(text("SELECT count(*) FROM processed_articles;"))
        proc_count = proc_count_res.scalar()
        print("Total rows in processed_articles:", proc_count)
        
        # Fetch some rows from articles
        res = await conn.execute(text("SELECT * FROM articles LIMIT 1;"))
        rows = res.fetchall()
        print("Articles (Read Model) columns:")
        for r in rows:
            print(list(r._mapping.keys()))
            
        # Fetch some rows from processed_articles
        res_proc = await conn.execute(text("SELECT id, title, slug, published_at FROM processed_articles LIMIT 5;"))
        rows_proc = res_proc.fetchall()
        print("Processed Articles rows:")
        for rp in rows_proc:
            print(dict(rp._mapping))

if __name__ == "__main__":
    asyncio.run(main())
