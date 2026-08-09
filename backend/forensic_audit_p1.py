"""
Phase 1 Post-Certification Forensic Audit
DO NOT MODIFY ANY PRODUCTION CODE.
Read-only investigation of the full editorial pipeline.
"""
import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.getcwd())

from sqlalchemy import select, func, text
from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel, ProcessedArticle, RawArticle
from app.models.source import Source
from app.models.projection import HomepageProjection

async def audit():
    async with AsyncSessionLocal() as session:
        # ============================================================
        # SECTION 1: Source Registry — All 11 Configured Sources
        # ============================================================
        print("=" * 80)
        print("SECTION 1: SOURCE REGISTRY (All 11 Configured Sources)")
        print("=" * 80)
        src_res = await session.execute(select(Source))
        sources = src_res.scalars().all()
        for s in sources:
            name = str(s.name).encode('ascii', 'replace').decode('ascii')
            print(f"\n  Source ID: {s.id}")
            print(f"  Name: {name}")
            print(f"  URL: {s.url}")
            print(f"  Method: {s.method}")
            print(f"  Enabled: {s.enabled}")
            print(f"  Health State: {s.health_state}")
            print(f"  Credibility Score: {s.credibility_score}")
            print(f"  Reliability Score: {s.reliability_score}")
            print(f"  Total Crawls: {s.total_crawls}")
            print(f"  Successful Crawls: {s.successful_crawls}")
            print(f"  Failure Count: {s.failure_count}")
            print(f"  Last Failure Type: {s.last_failure_type}")
            print(f"  Crawl Interval: {s.crawl_interval}s")
            print(f"  Last Crawl At: {s.last_crawl_at}")
            print(f"  Category: {s.category}")

        # ============================================================
        # SECTION 2: RawArticle Distribution per Source
        # ============================================================
        print("\n" + "=" * 80)
        print("SECTION 2: RAW ARTICLE DISTRIBUTION PER SOURCE")
        print("=" * 80)
        raw_res = await session.execute(
            select(Source.name, RawArticle.status, func.count(RawArticle.id))
            .outerjoin(RawArticle, Source.id == RawArticle.source_id)
            .group_by(Source.name, RawArticle.status)
            .order_by(Source.name)
        )
        raw_rows = raw_res.all()
        raw_by_source = defaultdict(dict)
        for name, status, cnt in raw_rows:
            raw_by_source[name][status or 'none'] = cnt
        for name, statuses in sorted(raw_by_source.items()):
            total = sum(statuses.values())
            n = str(name).encode('ascii', 'replace').decode('ascii')
            print(f"\n  {n}: {total} total RawArticles")
            for status, cnt in sorted(statuses.items()):
                print(f"    - {status}: {cnt}")

        # ============================================================
        # SECTION 3: ProcessedArticle Distribution per Source
        # ============================================================
        print("\n" + "=" * 80)
        print("SECTION 3: PROCESSED ARTICLE DISTRIBUTION PER SOURCE")
        print("=" * 80)
        proc_res = await session.execute(
            select(ProcessedArticle.source, func.count(ProcessedArticle.id))
            .group_by(ProcessedArticle.source)
            .order_by(func.count(ProcessedArticle.id).desc())
        )
        proc_rows = proc_res.all()
        for src, cnt in proc_rows:
            n = str(src).encode('ascii', 'replace').decode('ascii')
            print(f"  {n}: {cnt}")

        # ============================================================
        # SECTION 4: ArticleReadModel Distribution per Source
        # ============================================================
        print("\n" + "=" * 80)
        print("SECTION 4: ARTICLE READ MODEL DISTRIBUTION PER SOURCE")
        print("=" * 80)
        arm_res = await session.execute(
            select(ArticleReadModel.source, func.count(ArticleReadModel.id))
            .group_by(ArticleReadModel.source)
            .order_by(func.count(ArticleReadModel.id).desc())
        )
        arm_rows = arm_res.all()
        for src, cnt in arm_rows:
            n = str(src).encode('ascii', 'replace').decode('ascii')
            print(f"  {n}: {cnt}")

        # ============================================================
        # SECTION 5: Full Provenance of all 13 ArticleReadModel Rows
        # ============================================================
        print("\n" + "=" * 80)
        print("SECTION 5: FULL PROVENANCE TRACE (ArticleReadModel -> ProcessedArticle -> RawArticle)")
        print("=" * 80)
        arm_all_res = await session.execute(
            select(ArticleReadModel).order_by(ArticleReadModel.id)
        )
        arm_all = arm_all_res.scalars().all()
        for arm in arm_all:
            clean_title = str(arm.title).encode('ascii', 'replace').decode('ascii')[:60]
            print(f"\n  --- ArticleReadModel ID: {arm.id} ---")
            print(f"  Title: {clean_title}")
            print(f"  Source: {arm.source}")
            print(f"  Category: {arm.category}")
            print(f"  Publication Status: {arm.publication_status}")
            print(f"  Published At: {arm.published_at}")
            print(f"  Updated At: {arm.updated_at}")
            print(f"  URL: {arm.url}")
            print(f"  Is Test Data: {getattr(arm, 'is_test_data', 'N/A')}")

            # Trace to ProcessedArticle
            proc_stmt = select(ProcessedArticle).where(ProcessedArticle.id == int(arm.id))
            proc_r = await session.execute(proc_stmt)
            proc = proc_r.scalars().first()
            if proc:
                print(f"  -> ProcessedArticle ID: {proc.id}")
                print(f"     Source: {proc.source}")
                print(f"     Created At: {proc.created_at}")
                print(f"     Category ID: {proc.category_id}")
                raw_id = getattr(proc, 'raw_article_id', None)
                print(f"     Raw Article ID: {raw_id}")

                # Trace to RawArticle
                if raw_id:
                    raw_stmt = select(RawArticle).where(RawArticle.id == raw_id)
                    raw_r = await session.execute(raw_stmt)
                    raw = raw_r.scalars().first()
                    if raw:
                        print(f"  -> RawArticle ID: {raw.id}")
                        print(f"     Source ID: {raw.source_id}")
                        print(f"     URL: {raw.url}")
                        print(f"     Status: {raw.status}")
                        print(f"     Scraped At: {raw.scraped_at}")
                        print(f"     Is Test Data: {getattr(raw, 'is_test_data', False)}")
                        # Lookup the source
                        src_stmt = select(Source).where(Source.id == raw.source_id)
                        src_r = await session.execute(src_stmt)
                        src_obj = src_r.scalars().first()
                        if src_obj:
                            print(f"     Source Name: {src_obj.name}")
                            print(f"     Source Feed URL: {src_obj.url}")
                    else:
                        print(f"  -> RawArticle ID {raw_id}: NOT FOUND IN DB")
            else:
                print(f"  -> ProcessedArticle ID {arm.id}: NOT FOUND IN DB")

        # ============================================================
        # SECTION 6: Category Distribution of ArticleReadModel
        # ============================================================
        print("\n" + "=" * 80)
        print("SECTION 6: CATEGORY DISTRIBUTION OF ArticleReadModel")
        print("=" * 80)
        cat_res = await session.execute(
            select(ArticleReadModel.category, ArticleReadModel.source, func.count(ArticleReadModel.id))
            .group_by(ArticleReadModel.category, ArticleReadModel.source)
            .order_by(ArticleReadModel.category)
        )
        cat_rows = cat_res.all()
        cat_by_cat = defaultdict(list)
        for cat, src, cnt in cat_rows:
            cat_by_cat[cat].append((src, cnt))
        for cat, entries in sorted(cat_by_cat.items()):
            total = sum(cnt for _, cnt in entries)
            print(f"\n  Category: {cat} ({total} articles)")
            for src, cnt in entries:
                print(f"    - {src}: {cnt}")

        # ============================================================
        # SECTION 7: Deduplication Statistics per Source
        # ============================================================
        print("\n" + "=" * 80)
        print("SECTION 7: DEDUPLICATION STATISTICS PER SOURCE")
        print("=" * 80)
        dedup_res = await session.execute(
            select(Source.name, func.count(RawArticle.id))
            .outerjoin(RawArticle, Source.id == RawArticle.source_id)
            .where(RawArticle.status == 'deduplicated')
            .group_by(Source.name)
            .order_by(func.count(RawArticle.id).desc())
        )
        dedup_rows = dedup_res.all()
        for name, cnt in dedup_rows:
            n = str(name).encode('ascii', 'replace').decode('ascii')
            print(f"  {n}: {cnt} deduplicated")

        # ============================================================
        # SECTION 8: 'fetched' (eligible) articles per source
        # ============================================================
        print("\n" + "=" * 80)
        print("SECTION 8: FETCHED (ELIGIBLE) ARTICLES PER SOURCE")
        print("=" * 80)
        fetched_res = await session.execute(
            select(Source.name, func.count(RawArticle.id))
            .outerjoin(RawArticle, Source.id == RawArticle.source_id)
            .where(RawArticle.status == 'fetched')
            .group_by(Source.name)
            .order_by(func.count(RawArticle.id).desc())
        )
        fetched_rows = fetched_res.all()
        for name, cnt in fetched_rows:
            n = str(name).encode('ascii', 'replace').decode('ascii')
            print(f"  {n}: {cnt} fetched/eligible")

        # ============================================================
        # SECTION 9: 'filtered' articles per source
        # ============================================================
        print("\n" + "=" * 80)
        print("SECTION 9: FILTERED ARTICLES PER SOURCE")
        print("=" * 80)
        filt_res = await session.execute(
            select(Source.name, func.count(RawArticle.id))
            .outerjoin(RawArticle, Source.id == RawArticle.source_id)
            .where(RawArticle.status == 'filtered')
            .group_by(Source.name)
            .order_by(func.count(RawArticle.id).desc())
        )
        filt_rows = filt_res.all()
        if filt_rows:
            for name, cnt in filt_rows:
                n = str(name).encode('ascii', 'replace').decode('ascii')
                print(f"  {n}: {cnt} filtered/rejected")
        else:
            print("  No filtered articles found in any source.")

if __name__ == "__main__":
    asyncio.run(audit())
