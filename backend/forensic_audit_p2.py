"""
Phase 1 Post-Certification Forensic Audit - Part 2
HomepageBuilder scoring breakdown, source_profiles, ranking analysis.
DO NOT MODIFY ANY PRODUCTION CODE.
"""
import asyncio
import json
import os
import sys
import yaml
from datetime import datetime, timezone

sys.path.insert(0, os.getcwd())

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel
from app.models.projection import HomepageProjection
from app.editorial.homepage_builder import HomepageBuilder

async def audit_part2():
    # ============================================================
    # SECTION 10: source_profiles.yaml
    # ============================================================
    print("=" * 80)
    print("SECTION 10: SOURCE PROFILES (source_profiles.yaml)")
    print("=" * 80)
    profiles_path = os.path.join(os.getcwd(), "source_profiles.yaml")
    if os.path.exists(profiles_path):
        with open(profiles_path, 'r') as f:
            profiles = yaml.safe_load(f)
        print(json.dumps(profiles, indent=2, default=str))
    else:
        print(f"  source_profiles.yaml NOT FOUND at {profiles_path}")

    # ============================================================
    # SECTION 11: HomepageBuilder Scoring Breakdown for all candidates
    # ============================================================
    print("\n" + "=" * 80)
    print("SECTION 11: HOMEPAGE BUILDER SCORING BREAKDOWN")
    print("=" * 80)

    async with AsyncSessionLocal() as session:
        # Get all ArticleReadModel rows
        arm_res = await session.execute(select(ArticleReadModel).order_by(ArticleReadModel.published_at.desc()))
        all_articles = arm_res.scalars().all()
        print(f"\nTotal ArticleReadModel candidates: {len(all_articles)}")

        now = datetime.now(timezone.utc)
        for art in all_articles:
            clean_title = str(art.title).encode('ascii', 'replace').decode('ascii')[:50]
            age_hours = 0
            if art.published_at:
                age_hours = (now - art.published_at).total_seconds() / 3600

            # Manually compute freshness score as HomepageBuilder would
            freshness_score = max(0, 1.0 - (age_hours / 24.0))

            print(f"\n  ID: {art.id} | Source: {art.source} | Category: {art.category}")
            print(f"  Title: {clean_title}")
            print(f"  Published At: {art.published_at}")
            print(f"  Age (hours): {age_hours:.1f}")
            print(f"  Freshness Score (1 - age/24): {freshness_score:.4f}")
            print(f"  Final Score (from model): {getattr(art, 'final_score', 'N/A')}")
            print(f"  Trending Score: {getattr(art, 'trending_score', 'N/A')}")
            print(f"  Publication Status: {art.publication_status}")

    # ============================================================
    # SECTION 12: HomepageBuilder Source Code Analysis
    # ============================================================
    print("\n" + "=" * 80)
    print("SECTION 12: HOMEPAGE BUILDER ALGORITHM ANALYSIS")
    print("=" * 80)
    builder_path = os.path.join(os.getcwd(), "app", "editorial", "homepage_builder.py")
    if os.path.exists(builder_path):
        with open(builder_path, 'r') as f:
            lines = f.readlines()
        print(f"  File: {builder_path}")
        print(f"  Total lines: {len(lines)}")
        # Print the entire file for full transparency
        for i, line in enumerate(lines, 1):
            clean = line.rstrip().encode('ascii', 'replace').decode('ascii')
            print(f"  {i:4d}: {clean}")
    else:
        print(f"  homepage_builder.py NOT FOUND")

    # ============================================================
    # SECTION 13: diversity.py analysis
    # ============================================================
    print("\n" + "=" * 80)
    print("SECTION 13: EDITORIAL DIVERSITY MODULE")
    print("=" * 80)
    diversity_path = os.path.join(os.getcwd(), "app", "editorial", "diversity.py")
    if os.path.exists(diversity_path):
        with open(diversity_path, 'r') as f:
            lines = f.readlines()
        print(f"  File: {diversity_path}")
        print(f"  Total lines: {len(lines)}")
        for i, line in enumerate(lines, 1):
            clean = line.rstrip().encode('ascii', 'replace').decode('ascii')
            print(f"  {i:4d}: {clean}")
    else:
        print(f"  diversity.py NOT FOUND")

    # ============================================================
    # SECTION 14: Latest HomepageProjection Details
    # ============================================================
    print("\n" + "=" * 80)
    print("SECTION 14: LATEST HOMEPAGE PROJECTION DETAILS")
    print("=" * 80)
    async with AsyncSessionLocal() as session:
        hp_res = await session.execute(
            select(HomepageProjection).order_by(HomepageProjection.created_at.desc()).limit(1)
        )
        latest_hp = hp_res.scalars().first()
        if latest_hp:
            print(f"  Projection ID: {latest_hp.id}")
            print(f"  Version: {latest_hp.projection_version}")
            print(f"  Created At: {latest_hp.created_at}")
            stories = latest_hp.stories_json
            if isinstance(stories, list):
                print(f"  Stories Count: {len(stories)}")
                for idx, s in enumerate(stories, 1):
                    print(f"    {idx}. ID: {s.get('id')} | Title: {str(s.get('title', '')).encode('ascii', 'replace').decode('ascii')[:50]}")
                    print(f"       Score: {s.get('final_score', s.get('score', 'N/A'))}")
                    print(f"       Source: {s.get('source', 'N/A')}")
                    print(f"       Category: {s.get('category', 'N/A')}")
            elif isinstance(stories, dict):
                print(f"  Stories JSON keys: {list(stories.keys())}")
                articles_list = stories.get('articles', stories.get('stories', []))
                print(f"  Articles Count: {len(articles_list)}")
                for idx, s in enumerate(articles_list, 1):
                    print(f"    {idx}. ID: {s.get('id')} | Title: {str(s.get('title', '')).encode('ascii', 'replace').decode('ascii')[:50]}")
                    print(f"       Score: {s.get('final_score', s.get('score', 'N/A'))}")

    # ============================================================
    # SECTION 15: Publication Pipeline Rules
    # ============================================================
    print("\n" + "=" * 80)
    print("SECTION 15: PUBLICATION PIPELINE (ProcessedArticle -> ArticleReadModel)")
    print("=" * 80)
    # Check for publish/projection logic
    for fname in ["app/services/ranking/news_ranking_engine.py",
                   "app/editorial/publish.py",
                   "app/services/editorial_service.py"]:
        fpath = os.path.join(os.getcwd(), fname)
        if os.path.exists(fpath):
            print(f"\n  Found: {fname}")
            with open(fpath, 'r') as f:
                content = f.read()
            # Search for key terms
            for term in ["ArticleReadModel", "PUBLISHED", "publication_status", "publish"]:
                count = content.lower().count(term.lower())
                print(f"    References to '{term}': {count}")
        else:
            print(f"  Not found: {fname}")

if __name__ == "__main__":
    asyncio.run(audit_part2())
