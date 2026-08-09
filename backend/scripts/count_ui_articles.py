import asyncio
import urllib.request
import json
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle, ArticleReadModel

async def count_articles():
    async with AsyncSessionLocal() as db:
        proc_count = (await db.execute(select(ProcessedArticle))).scalars().all()
        read_count = (await db.execute(select(ArticleReadModel))).scalars().all()
        print(f"Database ProcessedArticles: {len(proc_count)}")
        print(f"Database ArticleReadModels: {len(read_count)}")
        for r in read_count:
            print(f"  [{r.id}] {r.title}")

    # Check API endpoints
    try:
        req_news = urllib.request.urlopen("http://localhost:8000/api/v1/news")
        data_news = json.loads(req_news.read().decode('utf-8'))
        articles_news = data_news if isinstance(data_news, list) else data_news.get("data", [])
        print(f"\nAPI /api/v1/news (Trending Feed) returned: {len(articles_news)} articles")
    except Exception as e:
        print(f"\nAPI /api/v1/news error: {e}")

    try:
        req_desks = urllib.request.urlopen("http://localhost:8000/api/v1/news/desks")
        desks = json.loads(req_desks.read().decode('utf-8'))
        total_desk_articles = sum(len(d.get("articles", [])) for d in desks)
        print(f"API /api/v1/news/desks (Category Desks) returned: {len(desks)} desks, containing {total_desk_articles} total articles")
    except Exception as e:
        print(f"API /api/v1/news/desks error: {e}")

if __name__ == "__main__":
    asyncio.run(count_articles())
