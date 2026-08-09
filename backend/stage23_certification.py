"""
Stage 2 & 3: Certification & Real-world Dry Run
===============================================
Executes the implemented map_category_slug from processor.py
against synthetic unit tests and 43 real-world DB articles.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel
from app.services.ingestion.processor import map_category_slug

SYNTHETIC_CASES = [
    ("OpenAI raises $6.5B Series M", "", "OpenAI Blog", "startups-and-business"),
    ("OpenAI lawsuit challenges new AI legislation", "", "OpenAI Blog", "technology"),
    ("OpenAI security vulnerability exposed in new CVE", "", "OpenAI Blog", "cybersecurity"),
    ("OpenAI launches new generative AI model", "", "OpenAI Blog", "artificial-intelligence"),
    ("A brief update", "", "OpenAI Blog", "technology"),
    ("NVIDIA announces new GPU architecture", "", "NVIDIA AI Blog", "hardware"),
    ("NVIDIA releases new open weights AI model", "", "NVIDIA AI Blog", "artificial-intelligence"),
    ("NVIDIA acquisition of AI startup blocked by regulators", "", "NVIDIA AI Blog", "technology"),
    ("NVIDIA facing Senate antitrust hearing", "", "NVIDIA AI Blog", "policy"),
    ("DeepMind robotics breakthrough", "The new robot", "Google DeepMind", "robotics"),
    ("AI model achieves breakthrough in weather forecasting", "", "Google DeepMind", "artificial-intelligence"),
    ("Breakthrough in quantum weather forecasting", "", "Google DeepMind", "science"),
    ("Apple announces new iPhone 16", "", "The Verge", "hardware"),
    ("Apple hit with EU antitrust fine", "", "The Verge", "policy"),
    ("Apple Services revenue grows in Q3", "", "The Verge", "startups-and-business"),
    ("AI startup raises seed funding", "", "TechCrunch", "startups-and-business"),
    ("Review: The new laptop is a disappointment", "", "TechCrunch", "hardware"),
    ("Cloudflare launches Kitesurf, a browser built for AI agents", "", "TechCrunch", "technology"),
    ("Today's the last day to get up to $400 off your TechCrunch Disrupt pass", "", "TechCrunch", "technology")
]

async def run_stage23():
    print("="*80)
    print("STAGE 2: SYNTHETIC CERTIFICATION (Adversarial Dataset)")
    print("="*80)
    
    passed = 0
    failed = 0
    for title, content, source, expected in SYNTHETIC_CASES:
        result = map_category_slug(title, content, source)
        if result == expected:
            print(f"[PASS] {title[:40].ljust(40)} -> {result}")
            passed += 1
        else:
            print(f"[FAIL] {title[:40].ljust(40)} -> Expected: {expected}, Got: {result}")
            failed += 1
            
    print(f"\nStage 2 Results: {passed} passed, {failed} failed")
    
    print("\n" + "="*80)
    print("STAGE 3: REAL-WORLD DRY RUN (43 Articles from DB)")
    print("="*80)
    
    async with AsyncSessionLocal() as db:
        stmt = select(ArticleReadModel.source).distinct()
        res = await db.execute(stmt)
        sources = res.scalars().all()
        
        articles = []
        for src in sources:
            s_stmt = select(ArticleReadModel).where(ArticleReadModel.source == src).limit(20)
            s_res = await db.execute(s_stmt)
            articles.extend(s_res.scalars().all())

    changes = 0
    fallbacks = 0
    
    for art in articles:
        prop = map_category_slug(art.title, art.content, art.source)
        curr = art.category.lower().replace(" ", "-") if art.category else "unknown"
        
        if prop == "technology":
            fallbacks += 1
        if curr != prop:
            changes += 1
            
    print(f"Total Articles Processed: {len(articles)}")
    print(f"Total Category Changes: {changes} ({(changes/len(articles))*100:.1f}%)")
    print(f"Articles falling back to 'technology': {fallbacks} ({(fallbacks/len(articles))*100:.1f}%)")
    
    print("\nSample Changes:")
    count = 0
    for art in articles:
        prop = map_category_slug(art.title, art.content, art.source)
        curr = art.category.lower().replace(" ", "-") if art.category else "unknown"
        if curr != prop and count < 10:
            print(f"ID {art.id} | {art.source} | {art.title[:50]}...")
            print(f"   {curr} -> {prop}")
            count += 1
            
    print("\n--- STAGE 4: STOP (Review Required) ---")
    print("Existing articles were NOT modified.")

if __name__ == "__main__":
    asyncio.run(run_stage23())
