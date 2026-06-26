"""
Reprocess all contaminated articles from their stored compressed HTML.

What this does:
  1. For each ProcessedArticle, decompress raw HTML from RawArticle
  2. Re-extract using the fixed HTMLAgent (source-aware selectors, quality validator)
  3. Update ProcessedArticle: content, clean_html, summary, reading_time
  4. Update ArticleReadModel: content, summary
  5. Delete ONLY known stub entity/topic links ('Tech Corp', 'Enterprise Software')
  6. Reset embedding_status so embeddings regenerate
  7. Enqueue run_article_intelligence_pipeline (Summary → Entities → Topics → Embeddings)
  8. Enqueue thumbnail re-download

Run from inside backend container:
  docker exec -it tech-news-backend python reprocess_articles.py

Or from host:
  docker exec tech-news-backend python reprocess_articles.py
"""

import asyncio
import re
import sys
import zlib
from datetime import datetime, timezone

from sqlalchemy import delete, select, update

from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel, ProcessedArticle, RawArticle
from app.models.source import Source
from app.models.tnt_knowledge import (
    ArticleEntityLink,
    ArticleTopicLink,
    EntityNode,
    TopicNode,
)
from agents.ingestion.html_agent import HTMLAgent
from app.services.ingestion.image_helper import extract_all_candidate_urls
from app.services.ingestion.processor import (
    calculate_reading_time,
    clean_and_sanitize_html,
    generate_seo_metadata,
)

# ── Stub data to remove (case-sensitive exact matches) ─────────────────────
STUB_ENTITY_IDS = {"company:tech_corp"}
STUB_TOPIC_NAMES = {"Enterprise Software"}


async def run() -> None:
    async with AsyncSessionLocal() as session:
        # ── Fetch all processed articles with their source info ─────────────
        stmt = (
            select(ProcessedArticle, Source)
            .outerjoin(Source, ProcessedArticle.source_id == Source.id)
        )
        rows = (await session.execute(stmt)).all()

        print(f"\n{'='*60}")
        print(f"Reprocessing {len(rows)} articles")
        print(f"{'='*60}\n")

        agent = HTMLAgent()
        ok_count = 0
        skip_count = 0
        fail_count = 0

        for proc_art, source_obj in rows:
            print(f"\n[{proc_art.id}] {proc_art.title[:70]}")

            # ── 1. Fetch raw article ────────────────────────────────────────
            raw_res = await session.execute(
                select(RawArticle).where(RawArticle.id == proc_art.raw_article_id)
            )
            raw_art = raw_res.scalar_one_or_none()

            if not raw_art:
                print(f"  → SKIP: no RawArticle (id={proc_art.raw_article_id})")
                skip_count += 1
                continue

            if not raw_art.compressed_html:
                print(f"  → SKIP: no compressed_html")
                skip_count += 1
                continue

            # ── 2. Decompress raw HTML ──────────────────────────────────────
            try:
                html_content = zlib.decompress(raw_art.compressed_html).decode("utf-8", errors="ignore")
            except Exception as exc:
                print(f"  → SKIP: decompress failed — {exc}")
                skip_count += 1
                continue

            # ── 3. Re-extract using fixed HTMLAgent ─────────────────────────
            source_name = source_obj.name if source_obj else None
            try:
                cleaned_payload = agent.clean_html(html_content, source_name=source_name)
            except Exception as exc:
                print(f"  → FAIL: clean_html raised — {exc}")
                fail_count += 1
                continue

            clean_text = cleaned_payload.get("clean_text", "")
            quality_valid = cleaned_payload.get("quality_valid", True)
            quality_reason = cleaned_payload.get("quality_reason", "?")
            content_score = cleaned_payload.get("content_score", 0)

            if not quality_valid or len(clean_text.strip()) < 100:
                # Fall back to stored clean_text if new extraction failed
                print(f"  ⚠ Quality check failed ({quality_reason}, score={content_score:.1f}). Using stored clean_text.")
                clean_text = raw_art.clean_text or proc_art.content or ""
            else:
                print(f"  ✓ Extracted {len(clean_text)} chars (score={content_score:.1f})")

            if not clean_text.strip():
                print(f"  → SKIP: no usable content after extraction")
                skip_count += 1
                continue

            # ── 4. Re-sanitize HTML for rendering ──────────────────────────
            clean_html_content = clean_and_sanitize_html(clean_text)

            # ── 5. Recompute derived fields ─────────────────────────────────
            reading_time = calculate_reading_time(clean_text)
            seo_meta = generate_seo_metadata(proc_art.title, clean_text)

            # ── 6. Build heuristic summary (2 sentences) ───────────────────
            sentences = re.split(r"(?<=[.!?])\s+", clean_text)
            new_summary = " ".join(sentences[:2])
            if len(new_summary) > 280:
                new_summary = new_summary[:277] + "..."
            if not new_summary.strip():
                new_summary = proc_art.summary or "No summary available."

            print(f"  Summary: {new_summary[:80]}...")

            # ── 7. Update ProcessedArticle ──────────────────────────────────
            await session.execute(
                update(ProcessedArticle)
                .where(ProcessedArticle.id == proc_art.id)
                .values(
                    content=clean_text,
                    clean_html=clean_html_content,
                    summary=new_summary,
                    reading_time=reading_time,
                    seo_keywords=seo_meta["seo_keywords"],
                    readability_score=seo_meta["readability_score"],
                    embedding_status="pending",      # mark stale
                    thumbnail_status="pending",      # reset thumbnail
                    thumbnail_url=None,
                    thumbnail_local=None,
                    image_url=None,
                    hero_image=None,
                )
            )

            # ── 8. Update ArticleReadModel ──────────────────────────────────
            await session.execute(
                update(ArticleReadModel)
                .where(ArticleReadModel.id == str(proc_art.id))
                .values(
                    content=clean_text,
                    summary=new_summary,
                    thumbnail_url=None,
                    thumbnail_local=None,
                    editorial_status="APPROVED",
                    publication_status="PUBLISHED",
                )
            )

            # ── 9. Remove ONLY known stub entity/topic links ────────────────
            # Delete stub ArticleEntityLinks
            await session.execute(
                delete(ArticleEntityLink).where(
                    ArticleEntityLink.article_id == str(proc_art.id),
                    ArticleEntityLink.entity_id.in_(STUB_ENTITY_IDS),
                )
            )
            # Delete stub ArticleTopicLinks
            await session.execute(
                delete(ArticleTopicLink).where(
                    ArticleTopicLink.article_id == str(proc_art.id),
                    ArticleTopicLink.topic_name.in_(STUB_TOPIC_NAMES),
                )
            )

            await session.commit()
            print(f"  ✓ DB updated (stub entities/topics cleared)")

            # ── 10. Enqueue Article Intelligence Pipeline ───────────────────
            try:
                from app.tasks.article_intelligence import run_article_intelligence_pipeline
                run_article_intelligence_pipeline.delay(proc_art.id)
                print(f"  ✓ Enqueued intelligence pipeline (Summary+Entities+Topics+Embedding)")
            except Exception as exc:
                print(f"  ⚠ Failed to enqueue intelligence pipeline: {exc}")

            # ── 11. Enqueue thumbnail re-download ───────────────────────────
            try:
                from celery_app import download_thumbnail_task
                candidates = extract_all_candidate_urls(html_content, raw_art.url)
                download_thumbnail_task.delay(proc_art.id, candidates[:5])
                print(f"  ✓ Enqueued thumbnail download ({len(candidates)} candidates)")
            except Exception as exc:
                print(f"  ⚠ Failed to enqueue thumbnail task: {exc}")

            ok_count += 1

        # ── Cleanup orphaned stub EntityNodes/TopicNodes ────────────────────
        print(f"\n{'='*60}")
        print("Cleaning up orphaned stub nodes...")

        # Remove EntityNode stubs that no longer have any article links
        for stub_id in STUB_ENTITY_IDS:
            link_count_res = await session.execute(
                select(ArticleEntityLink).where(ArticleEntityLink.entity_id == stub_id)
            )
            if not link_count_res.scalars().first():
                await session.execute(
                    delete(EntityNode).where(EntityNode.id == stub_id)
                )
                print(f"  Deleted orphaned EntityNode: {stub_id}")

        for stub_name in STUB_TOPIC_NAMES:
            link_count_res = await session.execute(
                select(ArticleTopicLink).where(ArticleTopicLink.topic_name == stub_name)
            )
            if not link_count_res.scalars().first():
                await session.execute(
                    delete(TopicNode).where(TopicNode.name == stub_name)
                )
                print(f"  Deleted orphaned TopicNode: {stub_name}")

        await session.commit()

        print(f"\n{'='*60}")
        print(f"DONE: {ok_count} reprocessed, {skip_count} skipped, {fail_count} failed")
        print(f"Intelligence pipeline tasks queued for {ok_count} articles.")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(run())
