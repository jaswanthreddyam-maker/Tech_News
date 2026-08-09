import asyncio
import json
import urllib.request
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:postgres_secure_pass@localhost:5433/tech_news_today"

async def forensic_trace():
    print("=" * 78)
    print(" FORENSIC RUNTIME DATA PIPELINE AUDIT REPORT")
    print("=" * 78)

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Stage 1: RawArticle
        raw_res = await session.execute(text("SELECT id, title, created_at FROM raw_articles ORDER BY created_at DESC LIMIT 5"))
        raw_rows = raw_res.fetchall()
        print(f"\n[STAGE 1: raw_articles] Count: {len(raw_rows)}")
        for r in raw_rows:
            print(f"  └─ ID: {r.id:4d} | Title: '{r.title[:45]}...' | Created: {r.created_at}")

        # Stage 2: ProcessedArticle
        proc_res = await session.execute(text("SELECT id, title, published_at, final_score FROM processed_articles ORDER BY published_at DESC LIMIT 5"))
        proc_rows = proc_res.fetchall()
        print(f"\n[STAGE 2: processed_articles] Count: {len(proc_rows)}")
        for p in proc_rows:
            print(f"  └─ ID: {p.id:4d} | Title: '{p.title[:45]}...' | Score: {p.final_score} | Published: {p.published_at}")

        # Stage 3: ArticleReadModel
        read_res = await session.execute(text("SELECT article_id, title, final_score, updated_at FROM article_read_models ORDER BY updated_at DESC LIMIT 5"))
        read_rows = read_res.fetchall()
        print(f"\n[STAGE 3: article_read_models] Count: {len(read_rows)}")
        for rm in read_rows:
            print(f"  └─ ID: {rm.article_id:4d} | Title: '{rm.title[:45]}...' | Score: {rm.final_score} | Updated: {rm.updated_at}")

        # Stage 4: HomepageProjection
        proj_res = await session.execute(text("SELECT id, version, checksum, created_at FROM homepage_projections ORDER BY created_at DESC LIMIT 5"))
        proj_rows = proj_res.fetchall()
        print(f"\n[STAGE 4: homepage_projections] Count: {len(proj_rows)}")
        for proj in proj_rows:
            print(f"  └─ ID: {proj.id:4d} | Version: {proj.version} | Checksum: {proj.checksum[:16]}... | Created: {proj.created_at}")

    # Stage 5: Redis Cache Inspection
    import redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    try:
        keys = [k.decode('utf-8') for k in r.keys('*')]
        print(f"\n[STAGE 5: Redis Cache] Total Keys: {len(keys)}")
        for k in keys[:10]:
            print(f"  └─ Key: {k}")
    except Exception as e:
        print(f"\n[STAGE 5: Redis Cache] Error: {e}")

    # Stage 6: REST API /api/v1/news Response Inspection
    try:
        req = urllib.request.Request("http://localhost:8000/api/v1/news")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            items = data.get("data", [])
            print(f"\n[STAGE 6: API Gateway /api/v1/news] Returned Items: {len(items)}")
            for item in items[:5]:
                print(f"  └─ ID: {item.get('id')} | Title: '{item.get('title', '')[:45]}...' | Source: {item.get('source_name')}")
    except Exception as e:
        print(f"\n[STAGE 6: API Gateway /api/v1/news] Error: {e}")

    print("\n" + "=" * 78)
    print(" FORENSIC TRACE COMPLETE")
    print("=" * 78)

if __name__ == "__main__":
    asyncio.run(forensic_trace())
