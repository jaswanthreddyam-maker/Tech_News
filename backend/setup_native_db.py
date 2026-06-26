import asyncpg
import asyncio

async def setup():
    conn = await asyncpg.connect(
        host="127.0.0.1", port=5432, user="postgres",
        password="mnbvcxzlkjhgfdsapoiuytrewq", database="postgres"
    )
    exists = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = 'tech_news_today'"
    )
    if not exists:
        await conn.execute("CREATE DATABASE tech_news_today")
        print("Created database tech_news_today")
    else:
        print("Database tech_news_today already exists")
    await conn.close()

    conn2 = await asyncpg.connect(
        host="127.0.0.1", port=5432, user="postgres",
        password="mnbvcxzlkjhgfdsapoiuytrewq", database="tech_news_today"
    )
    try:
        await conn2.execute("CREATE EXTENSION IF NOT EXISTS vector")
        print("pgvector extension enabled")
    except Exception as e:
        print(f"pgvector warning (may need install): {e}")
    await conn2.close()
    print("Done!")

asyncio.run(setup())
