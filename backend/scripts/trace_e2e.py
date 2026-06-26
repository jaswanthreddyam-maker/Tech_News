import asyncio
import logging
import os
import sys

# Setup paths so it can import app modules
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
root_dir = os.path.dirname(backend_dir)
sys.path.insert(0, root_dir)
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, 'app'))

from app.services.ingestion.rss_parser import RSSParser
from sqlalchemy import select

from app.apps.tnt.projectors import ArticleProjector
from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel, ProcessedArticle, RawArticle
from app.models.source import Source
from app.services.ingestion.image_helper import ImageProcessor
from app.services.ingestion.pipeline import PipelineOrchestrator

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def trace_e2e():
    print("=" * 60)
    print("E2E THUMBNAIL PIPELINE TRACE")
    print("=" * 60)

    # 1. Verify Storage Directories
    print("\n[STEP 1] Environment Verification")
    upload_dir = "/app/uploads/thumbnails"
    if not os.path.exists(upload_dir):
        print(f"UPLOAD_DIR ({upload_dir}) DOES NOT EXIST IN CONTAINER!")
    else:
        print(f"UPLOAD_DIR ({upload_dir}) exists.")

    local_upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads', 'thumbnails'))
    if not os.path.exists(local_upload_dir):
        print(f"LOCAL_UPLOAD_DIR ({local_upload_dir}) DOES NOT EXIST!")
    else:
        print(f"LOCAL_UPLOAD_DIR ({local_upload_dir}) exists.")

    print("\n[STEP 2] Database Inspection")
    async with AsyncSessionLocal() as session:
        # Pick one valid source
        source = (await session.execute(select(Source).where(Source.url.like("%theverge%")).limit(1))).scalar_one_or_none()
        if not source:
            source = (await session.execute(select(Source).where(Source.enabled == True).limit(1))).scalar_one_or_none()
        print(f"Selected Source: {source.name} ({source.url})")

        print("\n[STEP 3] RSS Fetch (Simulated)")
        # We will manually fetch one item and process it
        parser = RSSParser()
        feed_items = await parser.fetch_feed(source.url)
        if not feed_items:
            print("Failed to fetch RSS items.")
            return
        item = feed_items[0]
        print(f"Fetched RSS Item: {item.title}")
        print(f"RSS item image_url/thumbnail: {item.image_url} | {getattr(item, 'thumbnail', 'None')}")

        print("\n[STEP 4] Run Ingestion Pipeline (Single Article)")
        orchestrator = PipelineOrchestrator()
        try:
            # Injecting it via direct process_article to bypass celery and trace locally
            # First, check if already in RawArticle
            existing = (await session.execute(select(RawArticle).where(RawArticle.url == item.link))).scalar_one_or_none()
            if existing:
                print(f"Article already in RawArticle: {existing.id}. Deleting for trace.")
                await session.delete(existing)
                await session.commit()

            raw = RawArticle(
                title=item.title,
                url=item.link,
                source_id=source.id,
                url_hash=item.link,  # Fake hash
                title_hash=item.title,
                status="discovered",
                is_test_data=False
            )
            session.add(raw)
            await session.commit()
            await session.refresh(raw)
            print(f"Created RawArticle: {raw.id}")

            # Process Article
            processed = await orchestrator.processor.process(raw.id)
            if not processed:
                print("Processing failed.")
                return
            print(f"Created ProcessedArticle: {processed.id}")
            print(f"Initial ProcessedArticle.thumbnail_local: {processed.thumbnail_local}")
            print(f"Initial ProcessedArticle.thumbnail_url: {processed.thumbnail_url}")

            print("\n[STEP 5] Run Thumbnail Download Task")
            # Usually celery calls download_thumbnail_task. We call ImageProcessor manually.
            img_processor = ImageProcessor()
            # We must refresh processed article
            pa = (await session.execute(select(ProcessedArticle).where(ProcessedArticle.id == processed.id))).scalar_one()

            if not pa.image_url:
                print("No image_url on ProcessedArticle! Pipeline extraction failed to find candidate.")
            else:
                result = await img_processor.download_and_optimize(pa.image_url)
                print(f"ImageProcessor Result: {result}")

                # Check filesystem
                if result and result.get("thumbnail_local"):
                    path = result["thumbnail_local"].replace("/api/v1/", "")
                    # Local relative check
                    exists_local = os.path.exists(path)
                    print(f"Filesystem check for {path}: Exists={exists_local}")

                # Update PA
                if result:
                    pa.thumbnail_local = result.get("thumbnail_local")
                    pa.thumbnail_status = "completed"
                    await session.commit()
                    await session.refresh(pa)

            print("\n[STEP 6] Run Projection")
            projector = ArticleProjector()
            # Construct mock artifact payload
            artifact = {
                "url": pa.slug, # Articles read model uses slug as URL sometimes? Or url.
                "title": pa.title,
                "content": pa.content,
                "hash": "test_hash",
                "source": pa.source_name,
                "thumbnail_url": pa.thumbnail_url,
                "thumbnail_local": pa.thumbnail_local,
                "is_test_data": False
            }
            await projector.project(str(pa.id), artifact, session)
            print(f"Projected artifact ID {pa.id}")

            print("\n[STEP 7] Query Read Model")
            rm = (await session.execute(select(ArticleReadModel).where(ArticleReadModel.id == str(pa.id)))).scalar_one_or_none()
            if not rm:
                print("Article NOT FOUND in read model!")
            else:
                print(f"ReadModel.thumbnail_local: {rm.thumbnail_local}")
                print(f"ReadModel.is_test_data: {rm.is_test_data}")

            print("\n[STEP 8] Check API query exactly")
            # In news.py: stmt = select(ArticleReadModel).where(ArticleReadModel.is_test_data == False)
            sql = str(select(ArticleReadModel).where(ArticleReadModel.is_test_data == False).compile(compile_kwargs={"literal_binds": True}))
            print(f"Generated SQL for news API: {sql}")

            # Check how many rows match:
            c = (await session.execute(select(ArticleReadModel.id, ArticleReadModel.is_test_data).where(ArticleReadModel.is_test_data == False).limit(5))).fetchall()
            print("API Results (First 5 matching ArticleReadModel.is_test_data == False):")
            for r in c:
                print(r)

        except Exception as e:
            logger.exception("Trace failed")

if __name__ == "__main__":
    asyncio.run(trace_e2e())
