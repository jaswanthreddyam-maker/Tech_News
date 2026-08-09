import asyncio
import os
import httpx
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle, ProcessedArticle, ArticleReadModel
from app.services.ingestion.pipeline import process_raw_article_to_editorial
from app.core.config import settings

async def run_verification():
    async with AsyncSessionLocal() as db:
        # Find 5 RawArticles that have at least 5000 bytes of compressed_html (successfully scraped)
        res = await db.execute(select(RawArticle).order_by(RawArticle.id.desc()).limit(100))
        all_raws = res.scalars().all()
        
        valid_raws = []
        for ra in all_raws:
            if ra.compressed_html and len(ra.compressed_html) > 5000:
                valid_raws.append(ra)
            if len(valid_raws) == 5:
                break
                
        print(f"Found {len(valid_raws)} valid previously-scraped RawArticles.")
        
        proc_ids = []
        for ra in valid_raws:
            # Delete any existing downstream records
            await db.execute(delete(ProcessedArticle).where(ProcessedArticle.raw_article_id == ra.id))
            from app.services.ingestion.processor import generate_slug
            art_slug = generate_slug(ra.title)
            await db.execute(delete(ArticleReadModel).where(ArticleReadModel.url == art_slug))
            await db.commit()
            
            print(f"Processing existing RawArticle {ra.id} ({ra.title})")
            result = await process_raw_article_to_editorial(db, ra.id)
            if result.get("status") == "success":
                res_proc = await db.execute(select(ProcessedArticle).where(ProcessedArticle.raw_article_id == ra.id))
                proc_art = res_proc.scalars().first()
                if proc_art:
                    proc_ids.append(proc_art.id)
                    print(f" -> ProcessedArticle created: {proc_art.id}")
            else:
                print(f" -> Failed to process: {result}")
        
    print("Waiting 15 seconds for celery thumbnail tasks to complete...")
    await asyncio.sleep(15)
    
    stats = {
        "source_image_success": 0,
        "ai_fallback": 0,
        "placeholder": 0,
        "http_200": 0
    }
    
    async with httpx.AsyncClient() as client:
        async with AsyncSessionLocal() as db:
            for pid in proc_ids:
                res = await db.execute(select(ProcessedArticle).where(ProcessedArticle.id == pid))
                art = res.scalars().first()
                
                print("-" * 50)
                print(f"Article ID: {art.id}")
                print(f"Source: {art.source_name}")
                print(f"Thumbnail Status: {art.thumbnail_status}")
                print(f"Thumbnail Generation Reason: {art.thumbnail_generation_reason}")
                
                thumb_local = art.thumbnail_local
                thumb_url = art.thumbnail_url
                
                print(f"Thumbnail Local: {thumb_local}")
                print(f"Thumbnail URL: {thumb_url}")
                
                is_source = art.thumbnail_type in ('SOURCE', 'OG', 'TWITTER', 'HTML_IMG') if hasattr(art, 'thumbnail_type') else False
                is_ai = art.thumbnail_type == 'AI_GENERATED' if hasattr(art, 'thumbnail_type') else False
                is_placeholder = not thumb_local
                
                file_exists = False
                is_webp = False
                http_ok = False
                
                if thumb_local:
                    filename = thumb_local.split("/")[-1]
                    physical_path = os.path.join("/app/uploads/thumbnails", filename)
                    
                    file_exists = os.path.exists(physical_path)
                    print(f"Physical File Exists: {file_exists} ({physical_path})")
                    
                    if file_exists:
                        try:
                            from PIL import Image
                            with Image.open(physical_path) as img:
                                img.verify()
                                is_webp = img.format == "WEBP"
                            print(f"Is valid WEBP (Pillow): {is_webp}")
                        except Exception as e:
                            print(f"Is valid WEBP (Pillow): False (Error: {e})")
                            is_webp = False
                        
                        api_url = f"http://localhost:8000{thumb_local}"
                        try:
                            resp = await client.get(api_url)
                            print(f"HTTP Status: {resp.status_code}")
                            if resp.status_code == 200:
                                http_ok = True
                                stats["http_200"] += 1
                        except Exception as e:
                            print(f"HTTP Request failed: {e}")
                else:
                    stats["placeholder"] += 1
                    
                if not is_placeholder and file_exists and is_webp and http_ok:
                    if is_ai:
                        stats["ai_fallback"] += 1
                    else:
                        stats["source_image_success"] += 1
                        
    print("=" * 50)
    print("Verification Results:")
    print(f"Source image success: {stats['source_image_success']}/{len(proc_ids)}")
    print(f"AI fallback:          {stats['ai_fallback']}/{len(proc_ids)}")
    print(f"Placeholder:          {stats['placeholder']}/{len(proc_ids)}")
    print(f"HTTP 200:             {stats['http_200']}/{len(proc_ids)}")

if __name__ == "__main__":
    asyncio.run(run_verification())
