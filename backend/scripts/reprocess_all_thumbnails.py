import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle, ProcessedArticle, ArticleReadModel
from app.services.ingestion.image_helper import extract_all_candidate_urls, validate_and_score_thumbnail
from app.services.ingestion.pipeline import decompress_html
from app.editorial.homepage_builder import HomepageBuilder
import urllib.request
import json
import httpx
import os

async def reprocess():
    async with AsyncSessionLocal() as db:
        print("Re-evaluating thumbnail candidates for all processed articles...")
        stmt = select(ProcessedArticle)
        procs = (await db.execute(stmt)).scalars().all()

        for proc in procs:
            if not proc.raw_article_id:
                continue
            raw = (await db.execute(select(RawArticle).where(RawArticle.id == proc.raw_article_id))).scalars().first()
            if not raw or not raw.compressed_html:
                continue

            html = decompress_html(raw.compressed_html)
            candidates = extract_all_candidate_urls(html, raw.url)
            if not candidates:
                continue

            print(f"\n[{proc.id}] {proc.title[:35]}")
            print(f"  Top Candidate: {candidates[0]['source']} (Score: {candidates[0]['score']}) -> {candidates[0]['url'][:70]}")

            # Try candidates sequentially in fallback order
            winner = None
            for cand in candidates:
                val = await validate_and_score_thumbnail(cand["url"], cand["score"])
                if val:
                    winner = (cand, val)
                    break

            if winner:
                cand, val = winner
                # Save winner
                proc.thumbnail_url = cand["url"]
                proc.thumbnail_source = cand["source"]
                proc.winner_pass = "strict"
                proc.candidate_count = len(candidates)
                proc.thumbnail_status = "downloaded"
                proc.thumbnail_type = "REAL_IMAGE"

                # Save local file if needed
                ext = ".webp"
                filename = f"{proc.id}_{cand['source']}_{hash(cand['url']) & 0xffffffff:x}{ext}"
                local_dir = "/app/uploads/thumbnails"
                os.makedirs(local_dir, exist_ok=True)
                local_file_path = os.path.join(local_dir, filename)

                try:
                    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                        resp = await client.get(cand["url"])
                        if resp.status_code == 200:
                            with open(local_file_path, "wb") as f:
                                f.write(resp.content)
                            proc.thumbnail_local = f"/api/v1/uploads/thumbnails/{filename}"
                            print(f"  Downloaded & saved new winner: {proc.thumbnail_local}")
                except Exception as e:
                    print(f"  Failed download: {e}")

                # Update ReadModel
                read_art = (await db.execute(select(ArticleReadModel).where(ArticleReadModel.id == str(proc.id)))).scalars().first()
                if read_art:
                    read_art.thumbnail_local = proc.thumbnail_local
                    read_art.thumbnail_url = proc.thumbnail_url

        await db.commit()

        print("\nRebuilding Homepage & Category Desk Projections...")
        await HomepageBuilder.build_and_persist_homepage_projection(db)
        await HomepageBuilder.build_and_persist_category_desks(db)

    print("\nSUCCESS! All thumbnails re-processed and live API updated.")

if __name__ == "__main__":
    asyncio.run(reprocess())
