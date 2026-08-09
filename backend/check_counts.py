import sys
import os

current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres.grqjnmzteryrxfossice:Jaswanthreddy123456@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"

import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle, ProcessedArticle, ArticleReadModel

async def main():
  async with AsyncSessionLocal() as db:
    raw_cnt = (await db.execute(select(func.count(RawArticle.id)))).scalar()
    proc_cnt = (await db.execute(select(func.count(ProcessedArticle.id)))).scalar()
    read_cnt = (await db.execute(select(func.count(ArticleReadModel.id)))).scalar()
    print(f"RawArticle: {raw_cnt}")
    print(f"ProcessedArticle: {proc_cnt}")
    print(f"ArticleReadModel: {read_cnt}")

if __name__ == "__main__":
  asyncio.run(main())
