import asyncio
import json
import os
import sys
import urllib.request


def verify_step_1():
    print("==================================================")
    print("STEP 1 - Verify the API actually returns synthetic data")
    print("==================================================")
    try:
        req = urllib.request.Request('http://localhost:8000/api/v1/news')
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            articles = data.get('data', [])[:20]
            for a in articles:
                print(f"id: {a.get('id')}, title: {a.get('title')}, source: {a.get('source_name')}, is_test_data: {a.get('is_test_data', 'MISSING')}, thumbnail_local: {a.get('thumbnail_local')}, thumbnail_url: {a.get('thumbnail_url')}")
    except Exception as e:
        print(f"Error fetching from API: {e}")

async def async_verifications():
    from sqlalchemy import text

    from app.core.database import AsyncSessionLocal

    print("\n==================================================")
    print("STEP 2 - Verify SQL directly")
    print("==================================================")
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text("""
                SELECT title, source, is_test_data, thumbnail_local, thumbnail_url
                FROM articles
                ORDER BY published_at DESC
                LIMIT 30;
            """))
            for row in result:
                print(row)
        except Exception as e:
            print(f"Error running SQL: {e}")

    print("\n==================================================")
    print("STEP 6 - Verify thumbnail storage")
    print("==================================================")
    async with AsyncSessionLocal() as session:
        try:
            count = (await session.execute(text("SELECT COUNT(*) FROM processed_articles WHERE thumbnail_local IS NOT NULL;"))).scalar()
            print(f"ProcessedArticles with thumbnail_local: {count}")

            result = await session.execute(text("""
                SELECT thumbnail_local FROM processed_articles 
                WHERE thumbnail_local IS NOT NULL 
                LIMIT 20;
            """))
            for row in result:
                path = row[0]
                # Determine absolute path depending on how they are stored
                # if path starts with /api/v1/uploads, it might be served from backend/uploads
                fs_path = path.replace("/api/v1/", "")
                exists = os.path.exists(fs_path)
                print(f"DB path: {path} | FS path: {fs_path} | Exists: {exists}")
        except Exception as e:
            print(f"Error running SQL: {e}")

    print("\n==================================================")
    print("STEP 7 - Verify read model")
    print("==================================================")
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text("""
                SELECT pa.id, pa.thumbnail_local, a.thumbnail_local
                FROM processed_articles pa
                LEFT JOIN articles a ON pa.id = a.id
                WHERE pa.thumbnail_local IS NOT NULL OR a.thumbnail_local IS NOT NULL
                LIMIT 10;
            """))
            for row in result:
                print(f"ID: {row[0]}, Processed: {row[1]}, ReadModel: {row[2]}")
        except Exception as e:
            print(f"Error running SQL: {e}")

if __name__ == "__main__":
    verify_step_1()
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(async_verifications())
