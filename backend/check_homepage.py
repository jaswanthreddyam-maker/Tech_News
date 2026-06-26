import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text
from datetime import datetime, timedelta, timezone

async def run():
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)
        
        # Check what HomepageBuilder would find
        from sqlalchemy import select
        from app.models.article import ArticleReadModel
        
        stmt = select(ArticleReadModel).where(
            ArticleReadModel.is_test_data == False,
            ArticleReadModel.published_at >= cutoff
        )
        res = await db.execute(stmt)
        articles = res.scalars().all()
        print(f"HomepageBuilder candidates: {len(articles)}")
        for a in articles[:5]:
            print(f"  id={a.id[:8]}... title={a.title[:50]} final_score={a.final_score} pub={a.published_at}")
        
        # Also check raw SQL
        res2 = await db.execute(text("""
            SELECT COUNT(*) FROM articles
            WHERE is_test_data = false
            AND published_at >= NOW() - INTERVAL '24 hours'
        """))
        print(f"Raw SQL count: {res2.scalar()}")
        
        # Check if final_score is set
        res3 = await db.execute(text("""
            SELECT final_score, COUNT(*) 
            FROM articles 
            WHERE is_test_data = false
            GROUP BY final_score
            ORDER BY COUNT(*) DESC
        """))
        print("final_score distribution:")
        for r in res3.fetchall():
            print(f"  final_score={r[0]}: count={r[1]}")

        # Check the MINIMUM_EFFECTIVE_SCORE setting
        from app.core.config import settings
        min_score = getattr(settings, 'MINIMUM_EFFECTIVE_SCORE', 20.0)
        editorial_window = getattr(settings, 'EDITORIAL_WINDOW_HOURS', 24)
        print(f"\nMINIMUM_EFFECTIVE_SCORE: {min_score}")
        print(f"EDITORIAL_WINDOW_HOURS: {editorial_window}")
        
        # Try actually building homepage
        from app.editorial.homepage_builder import HomepageBuilder
        homepage_articles = await HomepageBuilder.build_homepage(db)
        print(f"\nHomepageBuilder returned: {len(homepage_articles)} articles")
        for a in homepage_articles[:5]:
            print(f"  {a.title[:60]}")

asyncio.run(run())
