import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as session:
        # Search by title in processed_articles
        res_proc = (await session.execute(text("SELECT id, title, slug, thumbnail_local FROM processed_articles WHERE title LIKE 'OpenAI Unveils GPT-5%'"))).fetchone()
        if res_proc:
            print("ProcessedArticle by title:")
            print("  ID:", res_proc[0])
            print("  Title:", res_proc[1])
            print("  Slug:", res_proc[2])
            print("  Thumbnail Local:", res_proc[3])
        else:
            print("ProcessedArticle with title like 'OpenAI Unveils GPT-5%' not found!")
            
        # Search by ID 905 in processed_articles
        res_proc_id = (await session.execute(text("SELECT id, title, slug, thumbnail_local FROM processed_articles WHERE id = 905"))).fetchone()
        if res_proc_id:
            print("ProcessedArticle by ID 905:")
            print("  ID:", res_proc_id[0])
            print("  Title:", res_proc_id[1])
            print("  Slug:", res_proc_id[2])
        else:
            print("ProcessedArticle with ID 905 not found!")

asyncio.run(check())
