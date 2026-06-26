import asyncio
from sqlalchemy import text
from app.core.database import async_engine

async def main():
    async with async_engine.connect() as conn:
        res = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public';
        """))
        tables = [r[0] for r in res.fetchall()]
        print("Tables in database:", tables)
        
        for table in tables:
            try:
                count_res = await conn.execute(text(f"SELECT count(*) FROM {table};"))
                count = count_res.scalar()
                print(f"Table '{table}': {count} rows")
            except Exception as e:
                print(f"Table '{table}': Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
