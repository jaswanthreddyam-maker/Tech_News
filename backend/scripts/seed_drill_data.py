import asyncio
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.article import Category, ProcessedArticle
from app.models.source import Source
from app.models.user import User


async def main():
    async with AsyncSessionLocal() as session:
        # 1. Create a user
        result = await session.execute(select(User).filter_by(email="drill@example.com"))
        user = result.scalars().first()
        if not user:
            user = User(
                email="drill@example.com", password_hash=hash_password("testpass"), name="Drill User", status="active"
            )
            session.add(user)
            await session.commit()

        # 2. Create a Category
        result = await session.execute(select(Category).filter_by(slug="drill-ai"))
        category = result.scalars().first()
        if not category:
            category = Category(name="Drill AI", slug="drill-ai")
            session.add(category)
            await session.commit()

        # 3. Create a Source
        result = await session.execute(select(Source).filter_by(name="Drill Source"))
        source = result.scalars().first()
        if not source:
            source = Source(
                name="Drill Source", category="ai", method="rss", url="https://example.com/rss", parser_version="1.0"
            )
            session.add(source)
            await session.commit()

        # 4. Create Processed Article
        result = await session.execute(select(ProcessedArticle).filter_by(slug="drill-article"))
        article = result.scalars().first()
        if not article:
            article = ProcessedArticle(
                source_id=source.id,
                category_id=category.id,
                title="This is a Drill Article",
                slug="drill-article",
                summary="Drill summary.",
                content="<p>Drill content.</p>",
                source="Drill Source",
                source_name="Drill Source",
                source_url="https://example.com/drill",
                ai_confidence=0.95,
                reading_time=2,
                published_status="published",
                tokens_used=100,
                final_score=50,
                freshness_score=50,
                engagement_score=50,
                is_archived=False,
            )
            session.add(article)
            await session.commit()

        print("Successfully seeded drill data!")


if __name__ == "__main__":
    asyncio.run(main())
