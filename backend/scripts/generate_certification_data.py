import argparse
import asyncio
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.article import Category, ProcessedArticle, RawArticle
from app.models.source import Source

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_or_create_dependencies(session):
    # Category
    stmt = select(Category).where(Category.slug == 'synthetic-test')
    category = (await session.execute(stmt)).scalars().first()
    if not category:
        category = Category(name='Synthetic Test', slug='synthetic-test')
        session.add(category)
        await session.flush()

    # Source
    stmt = select(Source).where(Source.name == 'Synthetic Generator')
    source = (await session.execute(stmt)).scalars().first()
    if not source:
        source = Source(
            name='Synthetic Generator',
            category='Tech',
            method='synthetic',
            url='https://synthetic.example.com',
            credibility_score=100,
            crawl_interval=3600,
            enabled=True,
            health_state='healthy',
            failure_count=0,
            parser_version='1.0',
            total_crawls=0,
            successful_crawls=0,
            reliability_score=1.0,
            is_deleted=False
        )
        session.add(source)
        await session.flush()
    return category, source

def get_fixture_html(profile_choice: str) -> str:
    base_url = "http://172.27.144.1:8081"
    valid_assets = ["valid.jpg", "transparent.png", "rotated_exif.jpg"]
    adversarial_assets = ["corrupt.jpg", "text.txt", "html.html", "bomb.jpg", "svg.svg", "animated.gif"]

    if profile_choice == "cqrs":
        return "<p>No images here. Pure CQRS.</p>"
    elif profile_choice == "valid":
        asset = random.choice(valid_assets)
        return f'<p>Testing valid pipeline.</p><img src="{base_url}/{asset}">'
    elif profile_choice == "broken":
        asset = random.choice(adversarial_assets)
        return f'<p>Broken image test.</p><img src="{base_url}/{asset}">'
    elif profile_choice == "exact_duplicate":
        return f'<p>Exact dup.</p><img src="{base_url}/valid.jpg">'
    elif profile_choice == "near_duplicate":
        return f'<p>Near dup.</p><img src="{base_url}/near_duplicate.jpg">'
    elif profile_choice == "filesystem_failure":
        return f'<p>Disk full test.</p><img src="{base_url}/enospc.jpg">'
    return "<p>Fallback.</p>"

async def generate_data(count: int, profile: str):
    async with AsyncSessionLocal() as session:
        category, source = await get_or_create_dependencies(session)

        logger.info(f"Generating {count} full-pipeline synthetic articles using profile: {profile}...")
        batch_size = 500
        now = datetime.now(timezone.utc)

        for i in range(count):
            uid = str(uuid.uuid4())

            if profile == "mixed":
                choices = ["cqrs", "valid", "valid", "broken", "exact_duplicate", "near_duplicate"]
                current_profile = random.choice(choices)
            else:
                current_profile = profile

            raw_html = get_fixture_html(current_profile)
            time_offset = timedelta(minutes=i)

            # RawArticle
            raw = RawArticle(
                source_id=source.id,
                title=f"Synthetic Article {uid}",
                url=f"https://synthetic.example.com/article/{uid}",
                url_hash=uid[:64],
                title_hash=uid[:64],
                clean_text=raw_html,
                status="processed",
                scraped_at=now - time_offset,
                processed_at=now - time_offset + timedelta(seconds=10),
                is_test_data=True
            )
            session.add(raw)
            await session.flush()

            # ProcessedArticle
            processed = ProcessedArticle(
                raw_article_id=raw.id,
                source_id=source.id,
                category_id=category.id,
                title=f"Synthetic Processed {uid} [{current_profile}]",
                slug=f"synthetic-processed-{uid}",
                summary="A synthetic certification summary.",
                content=raw_html,
                source="Synthetic Source",
                published_status="published",
                thumbnail_status="pending",
                is_test_data=True
            )
            session.add(processed)
            await session.flush()

            # Note: EventEnvelope and ReadModel generation is deferred to the
            # sync_projections script in the new pipeline certification flow.

            if i > 0 and i % batch_size == 0:
                await session.commit()
                logger.info(f"Committed {i} records...")

        await session.commit()
        logger.info(f"Successfully generated {count} synthetic records.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic workload data.")
    parser.add_argument("--count", type=int, default=100, help="Number of records to generate")
    parser.add_argument("--profile", type=str, choices=["cqrs", "valid", "broken", "mixed", "exact_duplicate", "near_duplicate"], default="mixed", help="Certification Profile to use")
    args = parser.parse_args()

    asyncio.run(generate_data(args.count, args.profile))
