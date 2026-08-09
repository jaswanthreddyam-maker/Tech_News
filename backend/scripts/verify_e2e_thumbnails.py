import asyncio
import os
import urllib.request
import json
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle, ArticleReadModel

async def verify_e2e():
    print("==================================================================")
    print("        END-TO-END THUMBNAIL PIPELINE PRODUCTION VERIFICATION    ")
    print("==================================================================")

    async with AsyncSessionLocal() as db:
        # 1. Fetch ProcessedArticles
        proc_stmt = select(ProcessedArticle).order_by(ProcessedArticle.id.desc())
        procs = (await db.execute(proc_stmt)).scalars().all()

        # 2. Fetch ArticleReadModels
        read_stmt = select(ArticleReadModel)
        reads = (await db.execute(read_stmt)).scalars().all()
        read_map = {r.id: r for r in reads}

        print(f"\n[1 & 2] DB Consistency Check ({len(procs)} Processed vs {len(reads)} ReadModels):")
        db_valid_count = 0
        for p in procs:
            r = read_map.get(str(p.id))
            r_local = r.thumbnail_local if r else None
            p_local = p.thumbnail_local

            is_match = (p_local == r_local) and (p_local is not None)
            if is_match:
                db_valid_count += 1

            status_icon = "✅" if is_match else "⚠️"
            print(f"  {status_icon} ID {p.id}: {p.title[:35]}")
            print(f"      Processed: source={p.thumbnail_source}, winner_pass={p.winner_pass}, local={p_local}")
            print(f"      ReadModel: local={r_local}")

        # 3 & 4. Disk File Existence & HTTP 200 Check
        print(f"\n[3 & 4] Physical Asset & HTTP Server Response Check:")
        http_success_count = 0
        for p in procs:
            local_url = p.thumbnail_local
            if not local_url:
                print(f"  ❌ ID {p.id}: No local thumbnail URL")
                continue

            file_path = local_url.replace("/api/v1/uploads/thumbnails/", "/app/uploads/thumbnails/")
            file_exists = os.path.exists(file_path)
            file_size = os.path.getsize(file_path) if file_exists else 0

            # HTTP Test via local fastAPI server
            http_status = 0
            content_type = ""
            try:
                full_http_url = f"http://localhost:8000{local_url}"
                req = urllib.request.urlopen(full_http_url)
                http_status = req.status
                content_type = req.headers.get("Content-Type", "")
            except Exception as e:
                http_status = str(e)

            http_ok = (http_status == 200) and file_exists and (file_size > 0)
            if http_ok:
                http_success_count += 1

            icon = "✅" if http_ok else "❌"
            print(f"  {icon} ID {p.id}: File Exists={file_exists} ({file_size} bytes) | HTTP={http_status} ({content_type})")

    # 5. Live Homepage API Check
    print(f"\n[5] Live Homepage API Payload Check (/api/v1/news):")
    try:
        req_api = urllib.request.urlopen("http://localhost:8000/api/v1/news")
        data = json.loads(req_api.read().decode('utf-8'))
        articles = data if isinstance(data, list) else data.get("data", [])
        print(f"  API returned {len(articles)} articles.")
        api_valid_count = 0
        for a in articles:
            has_thumb = bool(a.get("thumbnail_local"))
            if has_thumb:
                api_valid_count += 1
            print(f"    - ID {a.get('id')}: {a.get('title')[:35]} -> thumb: {a.get('thumbnail_local')}")
    except Exception as e:
        print(f"  ❌ API check failed: {e}")

    print("\n==================================================================")
    print(f"FINAL SUMMARY:")
    print(f"  DB Sync Status: {db_valid_count} / {len(procs)} synchronized")
    print(f"  HTTP 200 Served: {http_success_count} / {len(procs)} verified")
    print(f"  API Payload Valid: {api_valid_count} / {len(articles)} ready for Next.js")
    print("==================================================================")

if __name__ == "__main__":
    asyncio.run(verify_e2e())
