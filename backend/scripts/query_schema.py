import asyncio

from sqlalchemy import text

from app.core.database import AsyncSessionLocal


async def check():
    async with AsyncSessionLocal() as session:
        res = (await session.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'articles' AND column_name = 'is_test_data'"))).fetchall()
        print("Schema:", res)

        # Test query 1
        res2 = (await session.execute(text("SELECT count(*) FROM articles WHERE is_test_data = false"))).scalar()
        print("Count with false:", res2)

        # Test query 2
        res3 = (await session.execute(text("SELECT count(*) FROM articles WHERE is_test_data = true"))).scalar()
        print("Count with true:", res3)

        # Test query 3 - look at what's returned for FALSE
        res4 = (await session.execute(text("SELECT id, title, is_test_data FROM articles WHERE is_test_data = false LIMIT 5"))).fetchall()
        print("First 5 false:")
        for r in res4:
            print(r)

asyncio.run(check())
