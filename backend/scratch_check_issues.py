import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def run():
    async with AsyncSessionLocal() as db:
        print("=== THUMBNAIL STATUS COUNT ===")
        res_thumb_stats = await db.execute(text("""
            SELECT 
                COUNT(*) FILTER (WHERE thumbnail_local IS NOT NULL) AS local_not_null,
                COUNT(*) FILTER (WHERE thumbnail_status='downloaded') AS status_downloaded,
                COUNT(*) FILTER (WHERE thumbnail_status='failed') AS status_failed,
                COUNT(*) FILTER (WHERE thumbnail_status='pending') AS status_pending,
                COUNT(*) FILTER (WHERE thumbnail_type='AI_GENERATED') AS type_ai,
                COUNT(*) FILTER (WHERE thumbnail_type='FALLBACK') AS type_fallback,
                COUNT(*) FILTER (WHERE thumbnail_type='REAL_IMAGE') AS type_real
            FROM processed_articles;
        """))
        print(dict(res_thumb_stats.mappings().first()))
        
        print("\n=== DETAILED THUMBNAIL STATUS (LIMIT 15) ===")
        res_thumbs = await db.execute(text("""
            SELECT id, title, source, thumbnail_local, thumbnail_type, thumbnail_status
            FROM processed_articles
            ORDER BY id DESC
            LIMIT 15;
        """))
        for row in res_thumbs.mappings().all():
            print(dict(row))

if __name__ == "__main__":
    asyncio.run(run())
