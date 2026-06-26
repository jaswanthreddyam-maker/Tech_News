import asyncio
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.models.article import ProcessedArticle, RawArticle


async def main():
    print("Seeding representative data for recovery drill...")

    # 1. Ensure uploads directory exists and has some files
    uploads_dir = Path("/app/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, 6):
        thumb_path = uploads_dir / f"thumbnail_{i}.png"
        thumb_path.write_text(f"Dynamic thumbnail asset number {i} mock data")
        print(f"Created file: {thumb_path}")

    # 2. Database seeding
    async with AsyncSessionLocal() as db:
        # Clear tables (safe order: articles first, then raw)
        await db.execute(text("TRUNCATE TABLE articles CASCADE;"))
        await db.execute(text("TRUNCATE TABLE processed_articles CASCADE;"))
        await db.execute(text("TRUNCATE TABLE raw_articles CASCADE;"))

        # Insert raw articles
        for i in range(1, 6):
            raw_art = RawArticle(
                id=i,
                source_id=1,
                title=f"Breaking Tech News Story #{i}",
                url=f"https://example.com/story-{i}",
                url_hash=f"urlhash{i}",
                title_hash=f"titlehash{i}",
                compressed_html=b"mock html content",
                clean_text=f"This is the clean text content for breaking story number {i}.",
                article_metadata="{}",
                parser_version="1.0.0",
                scraped_at=datetime.now(timezone.utc),
                status="processed",
            )
            db.add(raw_art)

            # Insert matching processed articles
            proc_art = ProcessedArticle(
                id=i,
                raw_article_id=i,
                source_id=1,
                category_id=1,  # seeded by schema.sql
                title=f"Breaking Tech News Story #{i} (Processed)",
                slug=f"breaking-tech-news-story-{i}",
                summary=f"This is a premium AI summary of story #{i} explaining the major industry impacts.",
                content=f"Detailed editorial analysis of story #{i}.",
                source="TechCrunch",
                source_name="TechCrunch",
                source_url=f"https://example.com/story-{i}",
                thumbnail_url=f"/api/v1/uploads/thumbnail_{i}.png",
                thumbnail_local=f"/app/uploads/thumbnail_{i}.png",
                thumbnail_quality_score=90,
                thumbnail_hash=f"phash{i}",
                thumbnail_source="og:image",
                created_at=datetime.now(timezone.utc),
                editorial_status="APPROVED",
                publication_status="PUBLISHED"
            )
            db.add(proc_art)

            from app.models.article import ArticleReadModel
            read_model = ArticleReadModel(
                id=str(i),
                url=f"https://example.com/story-{i}",
                title=f"Breaking Tech News Story #{i} (Processed)",
                summary=f"This is a premium AI summary of story #{i} explaining the major industry impacts.",
                content=f"Detailed editorial analysis of story #{i}.",
                source="TechCrunch",
                published_at=datetime.now(timezone.utc),
                thumbnail_url=f"/api/v1/uploads/thumbnail_{i}.png",
                thumbnail_local=f"/app/uploads/thumbnail_{i}.png",
                hash=f"hash{i}",
                editorial_status="APPROVED",
                publication_status="PUBLISHED"
            )
            db.add(read_model)

        await db.commit()
        print(
            "Successfully seeded 5 raw articles, 5 processed articles, and alembic_version 'phase3_cert_rev' in PostgreSQL database."
        )


if __name__ == "__main__":
    asyncio.run(main())
