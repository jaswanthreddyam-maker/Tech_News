import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle, ProcessedArticle, ArticleReadModel
from app.services.ingestion.pipeline import process_raw_article_to_editorial
from app.editorial.homepage_builder import HomepageBuilder

async def process_more():
    async with AsyncSessionLocal() as db:
        proc_count = len((await db.execute(select(ProcessedArticle))).scalars().all())
        needed = 10 - proc_count
        print(f"Current ProcessedArticle count: {proc_count}. Needed: {needed}")

        if needed <= 0:
            print("Already have at least 10 articles!")
            return

        stmt = select(RawArticle).where(RawArticle.status == "filtered").limit(needed + 2)
        res = await db.execute(stmt)
        raw_candidates = res.scalars().all()
        print(f"Found {len(raw_candidates)} candidate RawArticles to process.")

        processed_ids = []
        for raw in raw_candidates:
            if len(processed_ids) >= needed:
                break
            print(f"Processing RawArticle ID {raw.id}: {raw.title[:40]}...")
            try:
                # Force status to pending so pipeline processes it
                raw.status = "pending"
                await db.commit()
                
                result = await process_raw_article_to_editorial(db, raw.id)
                print(f"  Result: {result}")
                processed_ids.append(raw.id)
            except Exception as e:
                print(f"  Error processing RawArticle {raw.id}: {e}")

        # Rebuild read model projections and category desks
        print("\nRebuilding category desks projections...")
        await HomepageBuilder.build_and_persist_category_desks(db)
        
        final_read_count = len((await db.execute(select(ArticleReadModel))).scalars().all())
        print(f"\nSUCCESS! Total ArticleReadModel count in UI: {final_read_count}")

if __name__ == "__main__":
    asyncio.run(process_more())
