import asyncio
import logging
from sqlalchemy import text, select
from app.core.database import async_engine
from app.core.storage_paths import StoragePathService

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger("tech_news.normalize_paths")

async def main():
    logger.info("Starting storage path normalization migration...")
    
    async with async_engine.connect() as conn:
        # 1. Update processed_articles table
        logger.info("Auditing processed_articles table...")
        res_pa = await conn.execute(
            text("SELECT id, thumbnail_local FROM processed_articles WHERE thumbnail_local IS NOT NULL")
        )
        pa_rows = res_pa.fetchall()
        
        pa_updated = 0
        for row in pa_rows:
            article_id, original_path = row[0], row[1]
            cleaned_path = StoragePathService.clean_relative(original_path)
            
            if cleaned_path != original_path:
                logger.info(f"ProcessedArticle ID {article_id}: '{original_path}' -> '{cleaned_path}'")
                await conn.execute(
                    text("UPDATE processed_articles SET thumbnail_local = :cleaned, image_url = :cleaned, hero_image = :cleaned WHERE id = :id"),
                    {"cleaned": cleaned_path, "id": article_id}
                )
                pa_updated += 1
                
        # 2. Update articles table (read model)
        logger.info("Auditing articles read model table...")
        res_art = await conn.execute(
            text("SELECT id, thumbnail_local FROM articles WHERE thumbnail_local IS NOT NULL")
        )
        art_rows = res_art.fetchall()
        
        art_updated = 0
        for row in art_rows:
            article_id, original_path = row[0], row[1]
            cleaned_path = StoragePathService.clean_relative(original_path)
            
            if cleaned_path != original_path:
                logger.info(f"ArticleReadModel ID {article_id}: '{original_path}' -> '{cleaned_path}'")
                await conn.execute(
                    text("UPDATE articles SET thumbnail_local = :cleaned WHERE id = :id"),
                    {"cleaned": cleaned_path, "id": article_id}
                )
                art_updated += 1
                
        await conn.commit()
        
    logger.info("=" * 60)
    logger.info("MIGRATION LOG SUMMARY")
    logger.info("=" * 60)
    logger.info(f"processed_articles updated: {pa_updated}")
    logger.info(f"articles (read model) updated: {art_updated}")
    logger.info("=" * 60)
    logger.info("Storage path normalization migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(main())
