import asyncio
import os
import urllib.request
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle

async def check():
    target_ids = [82, 83, 84, 85, 86]
    async with AsyncSessionLocal() as db:
        stmt = select(ProcessedArticle).where(ProcessedArticle.id.in_(target_ids))
        res = await db.execute(stmt)
        articles = res.scalars().all()
        
        for art in articles:
            print(f"[{art.id}] {art.title[:40]}")
            local_path = art.thumbnail_local
            if local_path and local_path.startswith("/api/v1/uploads/thumbnails/"):
                file_path = local_path.replace("/api/v1/uploads/thumbnails/", "/app/uploads/thumbnails/")
                exists = os.path.exists(file_path)
                size = os.path.getsize(file_path) if exists else 0
                print(f"  File exists: {exists}, size: {size} bytes")
                
                url = f"http://localhost:8000{local_path}"
                try:
                    req = urllib.request.Request(url, method="HEAD")
                    with urllib.request.urlopen(req) as resp:
                        print(f"  HTTP Status: {resp.status}, Content-Type: {resp.headers.get('Content-Type')}")
                except Exception as e:
                    print(f"  HTTP Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
