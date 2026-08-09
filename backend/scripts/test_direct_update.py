import asyncio
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel

async def fix_and_verify():
    async with AsyncSessionLocal() as db:
        # Simulate what the projector does
        test_payload = {
            "article_id": "86",
            "thumbnail_local": "/api/v1/uploads/thumbnails/96d45ed464633b23.webp",
            "thumbnail_url": "https://images.ctfassets.net/kftzwdyauwt9/6RSPaWdKwEvT9xWx4IjQy2/a334438e4daf9f62c24541c00c212749/third-party-cyber-evaluations_16x9.png?w=1600&h=900&fit=fill",
            "status": "downloaded"
        }
        
        artifact_id = test_payload["article_id"]
        tl = test_payload.get("thumbnail_local")
        tu = test_payload.get("thumbnail_url")
        ts = test_payload.get("status", "downloaded")
        
        print(f"Executing UPDATE for article_id={artifact_id}")
        print(f"  Setting thumbnail_local={tl}")
        print(f"  Setting thumbnail_url={tu}")
        print(f"  Setting thumbnail_status={ts}")
        
        stmt = (
            update(ArticleReadModel)
            .where(ArticleReadModel.id == artifact_id)
            .values(
                thumbnail_local=tl,
                thumbnail_url=tu,
                thumbnail_status=ts
            )
        )
        
        res = await db.execute(stmt)
        print(f"  rowcount: {res.rowcount}")
        await db.commit()
        
        # Verify
        stmt2 = select(ArticleReadModel.id, ArticleReadModel.thumbnail_local, ArticleReadModel.thumbnail_url, ArticleReadModel.thumbnail_status).where(ArticleReadModel.id == artifact_id)
        res2 = await db.execute(stmt2)
        row = res2.first()
        if row:
            print(f"\n  AFTER UPDATE:")
            print(f"  id={row[0]} thumb_local={row[1]} thumb_url={row[2]} thumb_status={row[3]}")

asyncio.run(fix_and_verify())
