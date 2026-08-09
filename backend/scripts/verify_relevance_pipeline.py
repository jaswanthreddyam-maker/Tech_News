import asyncio
import json
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle, RawArticle
from app.services.ingestion.image_helper import extract_all_candidate_urls, validate_and_score_thumbnail
from app.services.ingestion.pipeline import decompress_html

async def run_relevance_verification():
    print("===================================================================================")
    print("      ARTICLE THUMBNAIL RELEVANCE GATE & DIAGNOSTICS SUITE (10-20 ARTICLES)       ")
    print("===================================================================================")

    async with AsyncSessionLocal() as db:
        procs = (await db.execute(select(ProcessedArticle).order_by(ProcessedArticle.id.desc()))).scalars().all()
        
        verified_articles = 0
        for proc in procs:
            if not proc.raw_article_id:
                continue
            raw = (await db.execute(select(RawArticle).where(RawArticle.id == proc.raw_article_id))).scalars().first()
            if not raw or not raw.compressed_html:
                continue

            html = decompress_html(raw.compressed_html)
            candidates = extract_all_candidate_urls(html, raw.url)

            verified_articles += 1
            print(f"\n-----------------------------------------------------------------------------------")
            print(f"ARTICLE #{verified_articles} [ID {proc.id}]")
            print(f"Title: {proc.title}")
            print(f"URL: {raw.url}")
            print(f"Total Candidates Extracted: {len(candidates)}")
            print("-----------------------------------------------------------------------------------")

            pass_candidates = [c for c in candidates if c.get("decision") == "PASS"]
            reject_candidates = [c for c in candidates if c.get("decision") == "REJECT"]

            # Print diagnostic breakdown for candidates
            for idx, c in enumerate(candidates):
                dec_icon = "✅ PASS" if c.get("decision") == "PASS" else "❌ REJECT"
                print(f"  Candidate #{idx+1}: {dec_icon} | Score: {c.get('score')} | Source: {c.get('source')}")
                print(f"    URL: {c.get('url')[:85]}")
                if c.get("decision") == "REJECT":
                    print(f"    Rejection Reason: {c.get('rejection_reason')}")
                else:
                    print(f"    Relevance Score: {c.get('relevance_score')} | Signals: {c.get('relevance_signals')} | Soft Negs: {c.get('negative_signals')}")

            # Sequential Fallback Simulation
            winner = None
            winner_reason = ""
            for c in pass_candidates:
                val = await validate_and_score_thumbnail(c["url"], c["score"])
                if val:
                    winner = (c, val)
                    winner_reason = f"Passed Relevance Gate & Technical Validation (Aspect Ratio: {val.get('aspect_ratio', 'N/A')}, Dims: {val.get('width')}x{val.get('height')})"
                    break
                else:
                    print(f"  [Fallback Triggered] Candidate {c['url'][:60]} failed technical validation, trying next...")

            print("\n  FINAL SELECTION FOR ARTICLE:")
            if winner:
                cand, val = winner
                print(f"    Winner Source: {cand['source']}")
                print(f"    Winner URL:    {cand['url']}")
                print(f"    Composite Score: {cand['score']}")
                print(f"    Relevance Signals: {cand['relevance_signals']}")
                print(f"    Selection Reason: {winner_reason}")
            else:
                print(f"    Winner: None (No valid source candidates passed relevance & validation -> Degrades to AI / CategoryPlaceholder)")

    print("\n===================================================================================")
    print(f"RELEVANCE SUITE COMPLETE — {verified_articles} ARTICLES EVALUATED")
    print("===================================================================================")

if __name__ == "__main__":
    asyncio.run(run_relevance_verification())
