"""
Forensic Audit Part 4: Detailed filtered article analysis.
For each filtered article, show title, URL, content snippet, and EXACT filtering reason.
"""
import asyncio
import os
import sys
import json

sys.path.insert(0, os.getcwd())

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import RawArticle
from app.models.source import Source

async def audit_filtered_details():
    async with AsyncSessionLocal() as session:
        print("=" * 80)
        print("FILTERED ARTICLES — FULL DETAIL WITH CONTENT SNIPPETS")
        print("=" * 80)
        
        res = await session.execute(
            select(RawArticle, Source.name, Source.credibility_score, Source.category)
            .join(Source, Source.id == RawArticle.source_id)
            .where(RawArticle.status == 'filtered')
            .order_by(Source.name, RawArticle.id)
        )
        all_filtered = res.all()
        
        for raw, src_name, cred, src_cat in all_filtered:
            title = (raw.title or 'NO TITLE').encode('ascii', 'replace').decode('ascii')
            url = (raw.url or 'NO URL').encode('ascii', 'replace').decode('ascii')
            clean_text = (raw.clean_text or '').encode('ascii', 'replace').decode('ascii')
            word_count = len(clean_text.split()) if clean_text else 0
            
            # Parse metadata for quality metrics
            meta = {}
            if raw.article_metadata:
                try:
                    meta = json.loads(raw.article_metadata)
                except:
                    pass
            
            quality = meta.get('quality_metrics', {})
            
            print(f"\n{'='*60}")
            print(f"  Source: {src_name} (credibility: {cred}, category: {src_cat})")
            print(f"  Title: {title}")
            print(f"  URL: {url}")
            print(f"  Word Count: {word_count}")
            print(f"  Content Snippet (first 200 chars): {clean_text[:200]}")
            print(f"  ---")
            print(f"  Extraction Confidence: {meta.get('extraction_confidence', 'N/A')}")
            print(f"  Content Source: {meta.get('content_source', 'N/A')}")
            print(f"  Quality State: {meta.get('quality_state', 'N/A')}")
            print(f"  Quality Reason: {quality.get('reason', 'N/A')}")
            print(f"  Paragraph Count: {quality.get('paragraph_count', 'N/A')}")
            print(f"  Unique Ratio: {quality.get('unique_ratio', 'N/A')}")
            print(f"  Markup Ratio: {quality.get('markup_ratio', 'N/A')}")
            print(f"  Is Degraded: {quality.get('is_degraded', 'N/A')}")
            print(f"  RSS Fallback: {meta.get('rss_fallback', 'N/A')}")
            
            # Now manually check WHY it was filtered
            # Run the same checks from filter.py
            from app.services.ingestion.filter import evaluate_adaptive_quality, check_pre_ai_ingestion_eligibility
            
            meta_dict = {
                "source_category": src_cat,
                "source_name": src_name,
                "rss_fallback": meta.get('rss_fallback', False),
                "allow_rss_fallback": src_name in ["OpenAI Blog", "Ars Technica"],
                "author": meta.get('author'),
                "publish_date": meta.get('publish_date'),
                "seo_keywords": "",
            }
            
            quality_result = evaluate_adaptive_quality(
                title=raw.title or '',
                content=raw.clean_text or '',
                raw_html='x' * 1000,  # dummy
                meta_dict=meta_dict
            )
            
            relevance_result = check_pre_ai_ingestion_eligibility(
                title=raw.title or '',
                content=raw.clean_text or '',
                source_credibility=cred
            )
            
            print(f"  ---RECHECK---")
            print(f"  Quality Eligible: {quality_result.get('eligible')}")
            print(f"  Quality Reason: {quality_result.get('reason', 'PASSED')}")
            print(f"  Relevance Eligible: {relevance_result}")
            
        # Now show the PROCESSED articles for comparison
        print("\n\n" + "=" * 80)
        print("PROCESSED (PASSED) ARTICLES — CONTENT SNIPPETS FOR COMPARISON")
        print("=" * 80)
        
        res2 = await session.execute(
            select(RawArticle, Source.name, Source.credibility_score)
            .join(Source, Source.id == RawArticle.source_id)
            .where(RawArticle.status == 'processed')
            .order_by(Source.name, RawArticle.id)
        )
        all_processed = res2.all()
        
        for raw, src_name, cred in all_processed:
            title = (raw.title or 'NO TITLE').encode('ascii', 'replace').decode('ascii')
            clean_text = (raw.clean_text or '').encode('ascii', 'replace').decode('ascii')
            word_count = len(clean_text.split()) if clean_text else 0
            
            meta = {}
            if raw.article_metadata:
                try:
                    meta = json.loads(raw.article_metadata)
                except:
                    pass
            
            print(f"\n  Source: {src_name} | Title: {title[:60]}")
            print(f"  Words: {word_count} | Confidence: {meta.get('extraction_confidence', 'N/A')}")
            print(f"  Content Source: {meta.get('content_source', 'N/A')}")
            print(f"  Snippet: {clean_text[:150]}")

if __name__ == "__main__":
    asyncio.run(audit_filtered_details())
