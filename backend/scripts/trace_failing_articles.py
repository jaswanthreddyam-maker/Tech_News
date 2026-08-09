import asyncio
import os
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle, ProcessedArticle, ArticleReadModel
from app.core.config import settings

async def trace_articles(article_ids):
    async with AsyncSessionLocal() as db:
        for aid in article_ids:
            print(f"\n{'='*60}")
            print(f"TRACING ARTICLE ID: {aid}")
            print(f"{'='*60}")
            
            # 1. ProcessedArticle
            stmt = select(ProcessedArticle).where(ProcessedArticle.id == aid)
            res = await db.execute(stmt)
            proc = res.scalars().first()
            if not proc:
                print(f"  ProcessedArticle {aid} NOT FOUND!")
                continue
            
            print(f"\n[LAYER 2] ProcessedArticle:")
            print(f"  id:                          {proc.id}")
            print(f"  title:                       {proc.title}")
            print(f"  thumbnail_status:            {proc.thumbnail_status}")
            print(f"  thumbnail_generation_reason: {proc.thumbnail_generation_reason}")
            print(f"  thumbnail_type:              {getattr(proc, 'thumbnail_type', 'N/A')}")
            print(f"  thumbnail_local:             {proc.thumbnail_local}")
            print(f"  thumbnail_url:               {proc.thumbnail_url}")
            print(f"  candidate_count:             {proc.candidate_count}")
            
            # 2. RawArticle
            raw_id = proc.raw_article_id
            print(f"\n[LAYER 1] RawArticle (ID: {raw_id}):")
            if raw_id:
                stmt_raw = select(RawArticle).where(RawArticle.id == raw_id)
                res_raw = await db.execute(stmt_raw)
                raw = res_raw.scalars().first()
                if raw:
                    print(f"  URL:                    {raw.url}")
                    has_html = bool(raw.compressed_html)
                    html_size = len(raw.compressed_html) if raw.compressed_html else 0
                    print(f"  compressed_html exists: {has_html}")
                    print(f"  compressed_html size:   {html_size} bytes")
                    meta = raw.article_metadata
                    if meta:
                        print(f"  article_metadata keys:  {list(meta.keys()) if isinstance(meta, dict) else 'non-dict'}")
                    else:
                        print(f"  article_metadata:       None")
                else:
                    print("  RawArticle NOT FOUND in DB")
            else:
                print("  No raw_article_id link")
            
            # 3. ArticleReadModel
            print(f"\n[LAYER 3] ArticleReadModel:")
            stmt_read = select(ArticleReadModel).where(ArticleReadModel.id == str(aid))
            res_read = await db.execute(stmt_read)
            read_model = res_read.scalars().first()
            
            if read_model:
                print(f"  id:               {read_model.id}")
                print(f"  thumbnail_local:  {read_model.thumbnail_local}")
                print(f"  thumbnail_url:    {read_model.thumbnail_url}")
                print(f"  thumbnail_status: {read_model.thumbnail_status}")
                print(f"  thumbnail_type:   {getattr(read_model, 'thumbnail_type', 'N/A')}")
            else:
                print(f"  ArticleReadModel {aid} NOT FOUND!")
            
            # 4. Physical thumbnail
            print(f"\n[LAYER 4] Physical Thumbnail:")
            thumb_local = None
            if proc.thumbnail_local:
                thumb_local = proc.thumbnail_local
                print(f"  (source: ProcessedArticle)")
            elif read_model and read_model.thumbnail_local:
                thumb_local = read_model.thumbnail_local
                print(f"  (source: ArticleReadModel)")
                
            if thumb_local:
                filename = thumb_local.split("/")[-1]
                physical_path = os.path.join("/app/uploads/thumbnails", filename)
                file_exists = os.path.exists(physical_path)
                print(f"  path:    {physical_path}")
                print(f"  exists:  {file_exists}")
                if file_exists:
                    try:
                        from PIL import Image
                        with Image.open(physical_path) as img:
                            img.verify()
                            is_webp = img.format == "WEBP"
                            dims = img.size
                        size_bytes = os.path.getsize(physical_path)
                        print(f"  WEBP:    {is_webp}")
                        print(f"  dims:    {dims}")
                        print(f"  size:    {size_bytes} bytes")
                    except Exception as e:
                        print(f"  WEBP:    False (Error: {e})")
            else:
                print("  NO thumbnail_local on either ProcessedArticle or ArticleReadModel")
                
            # 5. DIVERGENCE ANALYSIS
            print(f"\n[DIVERGENCE]")
            proc_thumb = proc.thumbnail_local
            read_thumb = read_model.thumbnail_local if read_model else None
            if proc_thumb and read_thumb:
                if proc_thumb == read_thumb:
                    print(f"  ProcessedArticle.thumbnail_local == ArticleReadModel.thumbnail_local ✅")
                else:
                    print(f"  MISMATCH!")
                    print(f"    ProcessedArticle: {proc_thumb}")
                    print(f"    ArticleReadModel: {read_thumb}")
            elif proc_thumb and not read_thumb:
                print(f"  ⚠️  ProcessedArticle has thumbnail_local but ArticleReadModel does NOT")
                print(f"      ProcessedArticle.thumbnail_local = {proc_thumb}")
                print(f"      ArticleReadModel.thumbnail_local = {read_thumb}")
                print(f"  >>> ROOT CAUSE: Projection did not propagate thumbnail to read model")
            elif not proc_thumb and not read_thumb:
                print(f"  ❌ BOTH ProcessedArticle and ArticleReadModel have NULL thumbnail_local")
                print(f"  >>> ROOT CAUSE: Thumbnail was never downloaded for this article")
            else:
                print(f"  ArticleReadModel has thumbnail_local but ProcessedArticle does NOT (unexpected)")

        # 6. Also check what the trending API would actually return
        print(f"\n{'='*60}")
        print(f"[LAYER 5] ACTUAL TRENDING API ARTICLES")
        print(f"{'='*60}")
        
        from app.editorial.homepage_builder import HomepageBuilder
        from app.models.homepage_projection import HomepageProjection
        
        stmt_hp = select(HomepageProjection).order_by(HomepageProjection.generated_at.desc()).limit(1)
        res_hp = await db.execute(stmt_hp)
        hp = res_hp.scalars().first()
        if hp:
            import json
            stories = json.loads(hp.stories_json) if isinstance(hp.stories_json, str) else hp.stories_json
            print(f"  HomepageProjection has {len(stories)} stories")
            for s in stories:
                sid = s.get("id", "?")
                stitle = s.get("title", "?")[:40]
                sthumb_local = s.get("thumbnail_local")
                sthumb_url = s.get("thumbnail_url")
                print(f"    ID {sid}: thumb_local={sthumb_local}, thumb_url={sthumb_url}, title={stitle}")
        else:
            print("  No HomepageProjection found")

if __name__ == "__main__":
    asyncio.run(trace_articles([86, 82, 83]))
