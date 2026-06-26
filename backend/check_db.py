import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres_secure_pass@db:5432/tech_news_today')
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, title, LEFT(content, 500) FROM processed_articles WHERE source_name='The Verge' LIMIT 3;"))
        for row in result:
            print(f"ID: {row[0]}")
            print(f"Title: {row[1]}")
            print(f"Content: {row[2]}")
            print("---")

if __name__ == '__main__':
    asyncio.run(main())
