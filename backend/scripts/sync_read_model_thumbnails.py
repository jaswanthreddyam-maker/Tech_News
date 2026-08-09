import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle, ArticleReadModel
from app.editorial.homepage_builder import HomepageBuilder
import urllib.request
import json

async def sync_thumbnails():
    async with AsyncSessionLocal() as db:
        print("Syncing thumbnails from ProcessedArticle to ArticleReadModel...")
        stmt = select(ProcessedArticle)
        procs = (await db.execute(stmt)).scalars().all()
        
        updated_count = 0
        for p in procs:
            if p.thumbnail_local and p.thumbnail_status == "downloaded":
                read_stmt = select(ArticleReadModel).where(ArticleReadModel.id == str(p.id))
                read_art = (await db.execute(read_stmt)).scalars().first()
                if read_art:
                    read_art.thumbnail_local = p.thumbnail_local
                    read_art.thumbnail_url = p.thumbnail_url
                    updated_count += 1

        await db.commit()
        print(f"Updated {updated_count} ArticleReadModel records with valid thumbnail paths.")

        print("\nRebuilding HomepageProjection & refreshing Redis cache...")
        articles = await HomepageBuilder.build_and_persist_homepage_projection(db)
        print(f"Homepage projection rebuilt! Total articles in ranking: {len(articles)}")

        await HomepageBuilder.build_and_persist_category_desks(db)
        print("Category desk projections rebuilt!")

    # Verify API
    req = urllib.request.urlopen("http://localhost:8000/api/v1/news")
    data = json.loads(req.read().decode('utf-8'))
    articles = data if isinstance(data, list) else data.get("data", [])
    print(f"\nAPI /api/v1/news returned {len(articles)} items.")
    for item in articles:
        print(f"  [{item['id']}] {item['title'][:35]} -> thumb: {item.get('thumbnail_local')}")

if __name__ == "__main__":
    asyncio.run(sync_thumbnails())
