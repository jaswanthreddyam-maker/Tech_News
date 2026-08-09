import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle, ArticleReadModel

async def inspect_new_thumbnails():
    new_ids = [87, 88, 89, 90, 91]
    async with AsyncSessionLocal() as db:
        print("=== ProcessedArticle Table ===")
        stmt = select(ProcessedArticle).where(ProcessedArticle.id.in_(new_ids))
        procs = (await db.execute(stmt)).scalars().all()
        for p in procs:
            print(f"[{p.id}] {p.title[:40]}")
            print(f"  thumbnail_status: {p.thumbnail_status}")
            print(f"  thumbnail_local: {p.thumbnail_local}")
            print(f"  thumbnail_url: {p.thumbnail_url}")
            print(f"  candidate_count: {p.candidate_count}")

        print("\n=== ArticleReadModel Table ===")
        stmt_read = select(ArticleReadModel).where(ArticleReadModel.id.in_([str(i) for i in new_ids]))
        reads = (await db.execute(stmt_read)).scalars().all()
        for r in reads:
            print(f"[{r.id}] {r.title[:40]}")
            print(f"  thumbnail_local: {r.thumbnail_local}")
            print(f"  thumbnail_url: {r.thumbnail_url}")

if __name__ == "__main__":
    asyncio.run(inspect_new_thumbnails())
