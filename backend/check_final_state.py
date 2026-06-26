import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def run():
    async with AsyncSessionLocal() as db:
        print('=== FINAL STATE CHECK ===')
        
        r = await db.execute(text('SELECT COUNT(*) FROM processed_articles WHERE is_test_data = false OR is_test_data IS NULL'))
        print(f'Real processed articles: {r.scalar()}')
        
        r = await db.execute(text("""
            SELECT thumbnail_status, COUNT(*) 
            FROM processed_articles 
            WHERE is_test_data = false OR is_test_data IS NULL 
            GROUP BY thumbnail_status
        """))
        print('Thumbnail status distribution:')
        for row in r.fetchall():
            print(f'  {row[0]}: {row[1]}')
        
        r = await db.execute(text("""
            SELECT COUNT(*) FROM processed_articles 
            WHERE key_takeaways IS NOT NULL 
            AND key_takeaways::text != 'null' 
            AND (is_test_data = false OR is_test_data IS NULL)
        """))
        print(f'With key_takeaways: {r.scalar()}')
        
        r = await db.execute(text('SELECT COUNT(*) FROM articles WHERE thumbnail_local IS NOT NULL'))
        print(f'Read model articles with thumbnail_local: {r.scalar()}')
        
        r = await db.execute(text("""
            SELECT COUNT(*) FROM articles 
            WHERE key_takeaways IS NOT NULL AND key_takeaways::text != 'null'
        """))
        print(f'Read model articles with key_takeaways: {r.scalar()}')
        
        # Sample
        r = await db.execute(text("""
            SELECT id, title, thumbnail_local 
            FROM articles 
            WHERE thumbnail_local IS NOT NULL 
            LIMIT 3
        """))
        print('Sample articles with thumbnails:')
        for row in r.fetchall():
            print(f'  id={row[0]} title={str(row[1])[:40]} thumb={str(row[2])[:40]}')

asyncio.run(run())
