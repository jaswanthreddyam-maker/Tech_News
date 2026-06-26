"""
verify_pipeline.py — runs the Article Intelligence Pipeline for one article
synchronously to verify all 5 stages work end-to-end.

Usage:
  docker exec tech-news-worker python verify_pipeline.py [article_id]
"""
import asyncio
import sys

ARTICLE_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 22

async def run():
    import celery_app as ca
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    # Bootstrap worker context
    loop = asyncio.get_event_loop()
    engine = create_async_engine(settings.DATABASE_URL, pool_size=2)
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    ca.celery_engine = engine
    ca.CeleryAsyncSessionLocal = SessionLocal
    ca.worker_loop = loop

    from sqlalchemy import select
    from app.models.article import ProcessedArticle
    from app.models.tnt_knowledge import EntityNode, TopicNode, ArticleEntityLink, ArticleTopicLink
    from app.ai.service import AIService
    from app.ai.schemas import ArticleAIInput

    async with SessionLocal() as session:
        # Load article
        art = (await session.execute(
            select(ProcessedArticle).where(ProcessedArticle.id == ARTICLE_ID)
        )).scalars().first()

        if not art:
            print(f"❌ Article {ARTICLE_ID} not found")
            return

        content = art.content or ""
        print(f"\n{'='*60}")
        print(f"Article: {art.title[:60]}")
        print(f"Source:  {art.source_name}")
        print(f"Content: {len(content)} chars")
        print(f"Preview: {content[:120]}...")
        print(f"{'='*60}\n")

        # Verify content is clean
        nav_markers = ["The homepage", "Tech Reviews", "See all tech", "Sign in", "Subscribe"]
        contaminated = any(m in content[:500] for m in nav_markers)
        print(f"Content contamination check: {'❌ CONTAMINATED' if contaminated else '✅ CLEAN'}")

        # Run entity extraction
        print("\n[Stage 2] Entity Extraction...")
        ai_input = ArticleAIInput(title=art.title, content=content, source=art.source_name)
        svc = AIService()
        entities = await svc.extract_entities(ai_input)
        print(f"  Raw entities from LLM: {len(entities)}")
        for e in entities[:5]:
            print(f"    → {e.get('entity_type','?'):10} {e.get('canonical_name','?')} (conf={e.get('confidence',0):.2f})")

        # Run topic classification
        print("\n[Stage 3] Topic Classification...")
        topics = await svc.extract_topics(ai_input)
        print(f"  Raw topics from LLM: {len(topics)}")
        for t in topics:
            print(f"    → [{t.get('taxonomy_category','?')}] {t.get('name','?')} (conf={t.get('confidence',0):.2f})")

        # Check existing DB state
        existing_entities = (await session.execute(
            select(EntityNode.canonical_name, EntityNode.entity_type, ArticleEntityLink.confidence)
            .join(ArticleEntityLink, EntityNode.id == ArticleEntityLink.entity_id)
            .where(ArticleEntityLink.article_id == str(ARTICLE_ID))
        )).all()

        existing_topics = (await session.execute(
            select(TopicNode.name, TopicNode.taxonomy_category, ArticleTopicLink.confidence)
            .join(ArticleTopicLink, TopicNode.name == ArticleTopicLink.topic_name)
            .where(ArticleTopicLink.article_id == str(ARTICLE_ID))
        )).all()

        print(f"\n[DB State] Existing entities for article {ARTICLE_ID}: {len(existing_entities)}")
        for name, etype, conf in existing_entities:
            print(f"  {etype:12} {name} (conf={conf:.2f})")

        print(f"\n[DB State] Existing topics for article {ARTICLE_ID}: {len(existing_topics)}")
        for name, cat, conf in existing_topics:
            print(f"  [{cat}] {name} (conf={conf:.2f})")

        print(f"\n{'='*60}")
        print("✅ Verification complete.")

if __name__ == "__main__":
    asyncio.run(run())
