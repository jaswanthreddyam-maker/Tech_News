import asyncio
import traceback
import zlib
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle, ProcessedArticle
from app.services.ingestion.processor import clean_and_sanitize_html


async def rebuild_content():
    async with AsyncSessionLocal() as db:
        # Get all processed articles that are not test data
        stmt = (
            select(ProcessedArticle, RawArticle)
            .join(RawArticle, ProcessedArticle.raw_article_id == RawArticle.id)
            .where(ProcessedArticle.is_test_data == False)
        )
        
        result = await db.execute(stmt)
        rows = result.all()
        
        rebuilt_count = 0
        error_count = 0
        
        print(f"Found {len(rows)} articles to rebuild.")
        
        for processed, raw in rows:
            try:
                # Get HTML string
                if raw.compressed_html:
                    html_str = zlib.decompress(raw.compressed_html).decode("utf-8")
                elif raw.clean_text:
                    html_str = raw.clean_text
                else:
                    print(f"Skipping article {processed.id}: no raw html available")
                    continue
                    
                # Re-clean using updated logic
                new_clean_content = clean_and_sanitize_html(html_str)
                
                if new_clean_content:
                    processed.content = new_clean_content
                    # Nullify key takeaways so they will be regenerated
                    processed.key_takeaways = None
                    rebuilt_count += 1
                else:
                    print(f"Warning: clean_and_sanitize_html returned empty for {processed.id}")
                    
            except Exception as e:
                print(f"Failed to rebuild article {processed.id}: {e}")
                traceback.print_exc()
                error_count += 1
                
        await db.commit()
        print(f"Rebuild complete. Successfully updated {rebuilt_count} articles. Errors: {error_count}")


if __name__ == "__main__":
    asyncio.run(rebuild_content())
