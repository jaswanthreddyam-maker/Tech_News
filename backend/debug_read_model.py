import sys
import os

current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres.grqjnmzteryrxfossice:Jaswanthreddy123456@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel, ProcessedArticle

async def main():
  async with AsyncSessionLocal() as db:
    res = await db.execute(select(ArticleReadModel).limit(5))
    rms = res.scalars().all()
    print(f"ArticleReadModel sample ({len(rms)}):")
    for rm in rms:
      print(f"ID: {rm.id} | title: {rm.title[:30]} | thumb_url: {rm.thumbnail_url} | thumb_local: {rm.thumbnail_local}")

    res_p = await db.execute(select(ProcessedArticle).limit(5))
    pas = res_p.scalars().all()
    print(f"\nProcessedArticle sample ({len(pas)}):")
    for pa in pas:
      print(f"ID: {pa.id} | title: {pa.title[:30]} | thumb_url: {pa.thumbnail_url} | thumb_local: {pa.thumbnail_local}")

if __name__ == "__main__":
  asyncio.run(main())
