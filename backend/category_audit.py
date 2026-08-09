"""
Category Forensic Audit Script
==============================
Performs the read-only forensic audit for the category data flow.
"""
import asyncio
import os
import sys
import json
from collections import Counter
from sqlalchemy import select, func

sys.path.insert(0, os.getcwd())

from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel
from app.models.projection import CategoryDeskProjection

def safe_str(s, max_len=60):
    if not s:
        return "N/A"
    return s.encode("ascii", "replace").decode("ascii")[:max_len]

async def run_audit():
    async with AsyncSessionLocal() as db:
        print("=" * 80)
        print("PART 2 — DATABASE GROUND TRUTH")
        print("=" * 80)
        
        # Get AI Category Desk
        stmt = select(CategoryDeskProjection).where(CategoryDeskProjection.category_slug == "artificial-intelligence")
        res = await db.execute(stmt)
        ai_desk = res.scalars().first()
        
        if ai_desk and ai_desk.article_ids:
            ai_ids = ai_desk.article_ids
            art_stmt = select(ArticleReadModel).where(ArticleReadModel.id.in_(ai_ids))
            art_res = await db.execute(art_stmt)
            articles = art_res.scalars().all()
            
            print(f"Total AI desk articles found: {len(articles)}")
            correct_count = 0
            for art in articles:
                match = art.category == "Artificial Intelligence"
                if match: correct_count += 1
                print(f"ID: {art.id} | Title: {safe_str(art.title)} | Source: {art.source} | Stored Category: {art.category} | Match: {match}")
                
            print(f"Correct: {correct_count}/{len(articles)} ({(correct_count/len(articles))*100:.1f}%)")
        else:
            print("No articles in AI desk.")

        print("\n" + "=" * 80)
        print("PART 4 — CATEGORY ACCURACY TEST")
        print("=" * 80)
        
        # Sample 30 articles
        stmt = select(ArticleReadModel).limit(30)
        res = await db.execute(stmt)
        sample = res.scalars().all()
        for art in sample:
            print(f"ID: {art.id} | Source: {art.source} | Cat: {art.category} | Title: {safe_str(art.title)}")
            
        print("\n" + "=" * 80)
        print("PART 7 — CROSS-CATEGORY CONSISTENCY")
        print("=" * 80)
        
        # Check all desks
        stmt = select(CategoryDeskProjection)
        res = await db.execute(stmt)
        desks = res.scalars().all()
        for desk in desks:
            count = len(desk.article_ids) if desk.article_ids else 0
            print(f"Category Desk: {desk.category_slug} | Requested: {count}")
            
        print("\n" + "=" * 80)
        print("PART 8 — CATEGORY DISTRIBUTION")
        print("=" * 80)
        
        stmt = select(ArticleReadModel.category, func.count(ArticleReadModel.id)).group_by(ArticleReadModel.category)
        res = await db.execute(stmt)
        dist = res.all()
        
        total = sum(c for _, c in dist)
        for cat, c in dist:
            print(f"Category: {cat} | Count: {c} | Percent: {(c/total)*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(run_audit())
