"""
Forensic Audit Part 3: Investigate WHY articles are filtered.
Traces each filtered article back to its raw entry and the filter reason.
DO NOT MODIFY ANY PRODUCTION CODE.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())

from sqlalchemy import select, func, text
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle, ProcessedArticle
from app.models.source import Source

async def audit_filtering():
    async with AsyncSessionLocal() as session:
        # ============================================================
        # SECTION A: All filtered articles - detailed breakdown
        # ============================================================
        print("=" * 80)
        print("SECTION A: ALL FILTERED ARTICLES — DETAILED BREAKDOWN")
        print("=" * 80)
        
        filtered_res = await session.execute(
            select(RawArticle, Source.name)
            .join(Source, Source.id == RawArticle.source_id)
            .where(RawArticle.status == 'filtered')
            .order_by(Source.name, RawArticle.id)
        )
        filtered_articles = filtered_res.all()
        print(f"\nTotal filtered articles: {len(filtered_articles)}")
        
        for raw, source_name in filtered_articles:
            clean_title = str(raw.title or 'NO TITLE').encode('ascii', 'replace').decode('ascii')[:60]
            clean_url = str(raw.url or 'NO URL').encode('ascii', 'replace').decode('ascii')
            filter_reason = getattr(raw, 'filter_reason', None) or getattr(raw, 'rejection_reason', None) or 'UNKNOWN'
            print(f"\n  Source: {source_name}")
            print(f"  Raw ID: {raw.id}")
            print(f"  Title: {clean_title}")
            print(f"  URL: {clean_url}")
            print(f"  Filter Reason: {filter_reason}")
            print(f"  Scraped At: {raw.scraped_at}")

        # ============================================================
        # SECTION B: Check raw_article table schema for filter/rejection columns
        # ============================================================
        print("\n" + "=" * 80)
        print("SECTION B: RAW_ARTICLE TABLE COLUMNS")
        print("=" * 80)
        col_res = await session.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = 'raw_articles' ORDER BY ordinal_position"
        ))
        cols = col_res.all()
        for col_name, dtype in cols:
            print(f"  {col_name}: {dtype}")

        # ============================================================
        # SECTION C: All processed articles — per-source breakdown with scores
        # ============================================================
        print("\n" + "=" * 80)
        print("SECTION C: PROCESSED ARTICLES — PER-SOURCE WITH SCORES")
        print("=" * 80)
        proc_res = await session.execute(
            select(ProcessedArticle).order_by(ProcessedArticle.id)
        )
        all_proc = proc_res.scalars().all()
        for p in all_proc:
            clean_title = str(p.title or 'NO TITLE').encode('ascii', 'replace').decode('ascii')[:50]
            print(f"\n  Processed ID: {p.id}")
            print(f"  Source: {p.source}")
            print(f"  Title: {clean_title}")
            print(f"  Created At: {p.created_at}")
            print(f"  Impact Score: {getattr(p, 'impact_score', 'N/A')}")
            print(f"  AI Quality Score: {getattr(p, 'ai_quality_score', 'N/A')}")
            print(f"  Category ID: {p.category_id}")
            print(f"  Expires At: {getattr(p, 'expires_at', 'N/A')}")

        # ============================================================
        # SECTION D: Ingestion funnel summary
        # ============================================================
        print("\n" + "=" * 80)
        print("SECTION D: INGESTION FUNNEL SUMMARY")
        print("=" * 80)
        
        total_raw = await session.execute(select(func.count(RawArticle.id)))
        total_proc = await session.execute(select(func.count(ProcessedArticle.id)))
        
        # Per-source
        per_source = await session.execute(
            select(
                Source.name,
                func.count(RawArticle.id).filter(RawArticle.status == 'processed'),
                func.count(RawArticle.id).filter(RawArticle.status == 'filtered'),
                func.count(RawArticle.id).filter(RawArticle.status == 'deduplicated'),
                func.count(RawArticle.id)
            )
            .outerjoin(RawArticle, Source.id == RawArticle.source_id)
            .group_by(Source.name)
            .order_by(Source.name)
        )
        per_source_rows = per_source.all()
        
        print(f"\nTotal RawArticles: {total_raw.scalar()}")
        print(f"Total ProcessedArticles: {total_proc.scalar()}")
        print(f"\n{'Source':<25} {'Processed':>10} {'Filtered':>10} {'Deduped':>10} {'Total':>10} {'Pass%':>10}")
        print("-" * 75)
        for name, processed, filtered, deduped, total in per_source_rows:
            n = str(name).encode('ascii', 'replace').decode('ascii')[:24]
            pass_rate = f"{(processed/total*100):.1f}%" if total > 0 else "N/A"
            print(f"  {n:<23} {processed:>10} {filtered:>10} {deduped:>10} {total:>10} {pass_rate:>10}")

        # ============================================================
        # SECTION E: Check the filtering criteria in the code
        # ============================================================
        print("\n" + "=" * 80)
        print("SECTION E: FILTERING CODE ANALYSIS")
        print("=" * 80)
        # Search for filter-related logic
        for fname in [
            "app/services/ingestion/pipeline.py",
            "app/services/ingestion/persistence_service.py",
            "app/services/ingestion/content_filter.py",
            "app/services/ingestion/filters.py",
            "app/services/ingestion/quality_filter.py",
        ]:
            fpath = os.path.join(os.getcwd(), fname)
            if os.path.exists(fpath):
                with open(fpath, 'r') as f:
                    content = f.read()
                print(f"\n  Found: {fname} ({len(content)} bytes)")
                # Find lines with 'filter' or 'reject' or 'skip'
                for i, line in enumerate(content.splitlines(), 1):
                    lower = line.lower()
                    if any(kw in lower for kw in ['filter', 'reject', 'skip', 'exclude', 'discard', 'not_ai']):
                        clean = line.strip().encode('ascii', 'replace').decode('ascii')[:100]
                        if clean:
                            print(f"    Line {i}: {clean}")
            else:
                print(f"  Not found: {fname}")

if __name__ == "__main__":
    asyncio.run(audit_filtering())
