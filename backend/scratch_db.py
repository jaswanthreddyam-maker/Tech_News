import asyncio
from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel, ProcessedArticle
from app.models.source import Source
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        print("--- SOURCES ---")
        src_stmt = select(Source.id, Source.name, Source.url, Source.enabled)
        src_res = await db.execute(src_stmt)
        for row in src_res.all():
            print(f"ID={row.id} | Name={row.name} | URL={row.url} | Enabled={row.enabled}")

        print("\n--- ARTICLE READ MODELS ---")
        rm_stmt = select(
            ArticleReadModel.id, 
            ArticleReadModel.title, 
            ArticleReadModel.url, 
            ArticleReadModel.editorial_status, 
            ArticleReadModel.publication_status, 
            ArticleReadModel.is_test_data
        )
        rm_res = await db.execute(rm_stmt)
        for row in rm_res.all():
            print(f"ID={row.id} | Title={row.title} | URL={row.url} | Editorial={row.editorial_status} | Pub={row.publication_status} | Test={row.is_test_data}")

        print("\n--- PROCESSED ARTICLES ---")
        pa_stmt = select(
            ProcessedArticle.id, 
            ProcessedArticle.title, 
            ProcessedArticle.slug, 
            ProcessedArticle.editorial_status, 
            ProcessedArticle.publication_status, 
            ProcessedArticle.is_test_data
        )
        pa_res = await db.execute(pa_stmt)
        for row in pa_res.all():
            print(f"ID={row.id} | Title={row.title} | Slug={row.slug} | Editorial={row.editorial_status} | Pub={row.publication_status} | Test={row.is_test_data}")

if __name__ == "__main__":
    asyncio.run(main())
