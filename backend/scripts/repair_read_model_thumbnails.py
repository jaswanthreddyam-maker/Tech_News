"""
Repair script: Propagate thumbnail data from ProcessedArticle → ArticleReadModel
for all articles where ProcessedArticle has a valid thumbnail but ArticleReadModel does not.
"""
import asyncio
from sqlalchemy import select, update, cast, String
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle, ArticleReadModel

async def repair():
    async with AsyncSessionLocal() as db:
        # Find all ProcessedArticles that have a valid thumbnail_local
        # but whose corresponding ArticleReadModel has NULL thumbnail_local
        stmt = (
            select(ProcessedArticle)
            .where(
                ProcessedArticle.thumbnail_local.isnot(None),
                ProcessedArticle.thumbnail_status == "downloaded"
            )
        )
        res = await db.execute(stmt)
        proc_articles = res.scalars().all()

        repaired = 0
        already_ok = 0
        not_found = 0

        for proc in proc_articles:
            # Check the read model
            read_stmt = select(ArticleReadModel).where(ArticleReadModel.id == str(proc.id))
            read_res = await db.execute(read_stmt)
            read_model = read_res.scalars().first()

            if not read_model:
                print(f"  SKIP: ArticleReadModel for ProcessedArticle {proc.id} not found")
                not_found += 1
                continue

            if read_model.thumbnail_local == proc.thumbnail_local:
                already_ok += 1
                continue

            # REPAIR: propagate from ProcessedArticle to ArticleReadModel
            print(f"  REPAIR: Article {proc.id} ({proc.title[:40]}...)")
            print(f"    ProcessedArticle.thumbnail_local = {proc.thumbnail_local}")
            print(f"    ArticleReadModel.thumbnail_local  = {read_model.thumbnail_local} → {proc.thumbnail_local}")

            upd_stmt = (
                update(ArticleReadModel)
                .where(ArticleReadModel.id == str(proc.id))
                .values(
                    thumbnail_local=proc.thumbnail_local,
                    thumbnail_url=proc.thumbnail_url,
                    thumbnail_status=proc.thumbnail_status,
                    thumbnail_type=proc.thumbnail_type
                )
            )
            await db.execute(upd_stmt)
            repaired += 1

        await db.commit()
        print(f"\nDone. Repaired: {repaired}, Already OK: {already_ok}, Not Found: {not_found}")

if __name__ == "__main__":
    asyncio.run(repair())
