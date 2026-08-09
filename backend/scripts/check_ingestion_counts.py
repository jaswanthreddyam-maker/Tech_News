import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle, ProcessedArticle, ArticleReadModel

async def check_counts():
    async with AsyncSessionLocal() as db:
        raw_count = (await db.execute(select(func.count(RawArticle.id)))).scalar() or 0
        proc_count = (await db.execute(select(func.count(ProcessedArticle.id)))).scalar() or 0
        read_count = (await db.execute(select(func.count(ArticleReadModel.id)))).scalar() or 0

        print(f"Total Raw Articles (Scraped/Fetched): {raw_count}")
        print(f"Total Processed Articles (AI Enriched): {proc_count}")
        print(f"Total Read Model Articles (Published to UI): {read_count}")

        # List breakdown of raw articles by source
        raws = (await db.execute(select(RawArticle.source_name, func.count(RawArticle.id)).group_by(RawArticle.source_name))).all()
        print("\nRaw Articles by Source:")
        for source, cnt in raws:
            print(f"  - {source}: {cnt}")

if __name__ == "__main__":
    asyncio.run(check_counts())
