import asyncio
import asyncpg
import os

async def drop():
    db_url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg', 'postgresql')
    conn = await asyncpg.connect(db_url)
    await conn.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO public;')
    await conn.close()
    print("Database schema dropped and recreated.")

if __name__ == '__main__':
    asyncio.run(drop())
