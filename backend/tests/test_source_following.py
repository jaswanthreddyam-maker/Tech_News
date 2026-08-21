from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.models.article import ArticleReadModel, Category, ProcessedArticle
from app.models.followed_source import FollowedSource
from app.models.source import Source
from app.models.user import User
from app.services.personalization_service import PersonalizationService


@pytest_asyncio.fixture
async def cleanup_sources_test_data(db_session):
    # Cleanup before and after
    yield
    await db_session.execute(delete(FollowedSource))
    await db_session.commit()


@pytest.mark.asyncio
async def test_adversarial_source_attribution_and_following(db_session, cleanup_sources_test_data):
    """
    CRITICAL INVARIANT TEST:
    Following a source by slug means following articles published strictly by that source (source_id).
    Entity mentions, keyword mentions, or topic matching must NEVER cause an article
    from an unfollowed publisher to appear in the Following feed.
    """
    now = datetime.now(timezone.utc)

    # 1. Create test User
    user = User(
        name="Test Follower",
        email=f"follower_{int(now.timestamp())}@example.com",
        status="active",
    )
    db_session.add(user)
    await db_session.flush()

    # 2. Get or create Sources: OpenAI Blog and TechCrunch
    openai_res = await db_session.execute(select(Source).where(Source.slug == "openai"))
    openai_source = openai_res.scalars().first()
    if not openai_source:
        openai_source = Source(
            name="OpenAI Blog Test",
            slug="openai",
            category="official",
            method="rss",
            url="https://openai.com/test-rss",
            enabled=True,
            is_deleted=False,
        )
        db_session.add(openai_source)
        await db_session.flush()

    tc_res = await db_session.execute(select(Source).where(Source.slug == "techcrunch"))
    tc_source = tc_res.scalars().first()
    if not tc_source:
        tc_source = Source(
            name="TechCrunch Test",
            slug="techcrunch",
            category="editorial",
            method="rss",
            url="https://techcrunch.com/test-rss",
            enabled=True,
            is_deleted=False,
        )
        db_session.add(tc_source)
        await db_session.flush()

    cat_res = await db_session.execute(select(Category).limit(1))
    cat = cat_res.scalars().first()
    cat_id = cat.id if cat else 1

    # 3. Create Article A: Published by TechCrunch, but heavily mentions "OpenAI"
    art_a_id = 888001
    proc_a = ProcessedArticle(
        id=art_a_id,
        source_id=tc_source.id,
        category_id=cat_id,
        title="OpenAI announces massive new GPT-5 model at summit",
        slug=f"techcrunch-openai-gpt5-{int(now.timestamp())}",
        summary="TechCrunch reports on OpenAI's major announcement today.",
        content="OpenAI today announced their frontier model...",
        source=tc_source.name,
        editorial_status="APPROVED",
        publication_status="PUBLISHED",
        published_at=now - timedelta(minutes=10),
        is_test_data=False,
    )
    read_a = ArticleReadModel(
        id=str(art_a_id),
        slug=proc_a.slug,
        url=f"https://techcrunch.com/article-{art_a_id}",
        title=proc_a.title,
        summary=proc_a.summary,
        content=proc_a.content,
        source=tc_source.name,
        editorial_status="APPROVED",
        publication_status="PUBLISHED",
        published_at=proc_a.published_at,
        hash=f"hash-{art_a_id}",
        is_test_data=False,
    )

    # 4. Create Article B: Published by OpenAI Blog directly
    art_b_id = 888002
    proc_b = ProcessedArticle(
        id=art_b_id,
        source_id=openai_source.id,
        category_id=cat_id,
        title="Introducing GPT-5: A frontier intelligence release",
        slug=f"openai-introducing-gpt5-{int(now.timestamp())}",
        summary="Official release notes directly from OpenAI research.",
        content="We are releasing GPT-5 today across all tiers...",
        source=openai_source.name,
        editorial_status="APPROVED",
        publication_status="PUBLISHED",
        published_at=now - timedelta(minutes=5),
        is_test_data=False,
    )
    read_b = ArticleReadModel(
        id=str(art_b_id),
        slug=proc_b.slug,
        url=f"https://openai.com/news/article-{art_b_id}",
        title=proc_b.title,
        summary=proc_b.summary,
        content=proc_b.content,
        source=openai_source.name,
        editorial_status="APPROVED",
        publication_status="PUBLISHED",
        published_at=proc_b.published_at,
        hash=f"hash-{art_b_id}",
        is_test_data=False,
    )

    db_session.add_all([proc_a, read_a, proc_b, read_b])
    await db_session.commit()

    service = PersonalizationService(db_session)

    # 5. User follows ONLY OpenAI via canonical slug
    await service.follow_source(user_id=user.id, source_ref="openai")

    # 6. Fetch Following Feed
    feed = await service.get_source_following_feed(user_id=user.id)
    articles = feed["items"]
    article_ids = [a.id for a in articles]

    # Verification:
    # - Article B (published by OpenAI) MUST be in the feed
    # - Article A (published by TechCrunch about OpenAI) MUST NOT be in the feed
    assert str(art_b_id) in article_ids, "Article published by OpenAI must appear in Following feed"
    assert str(art_a_id) not in article_ids, "Article published by TechCrunch mentioning OpenAI must NOT appear in Following feed"
    assert feed["followed_sources_count"] == 1


async def get_or_create_source(db_session, slug: str, name: str, category: str = "official", url: str = "https://example.com/rss") -> Source:
    res = await db_session.execute(select(Source).where(Source.slug == slug))
    src = res.scalars().first()
    if not src:
        src = Source(
            name=name,
            slug=slug,
            category=category,
            method="rss",
            url=url,
            enabled=True,
            is_deleted=False,
        )
        db_session.add(src)
        await db_session.flush()
    return src


@pytest.mark.asyncio
async def test_follow_idempotency_and_unfollow(db_session, cleanup_sources_test_data):
    """
    Test that following a source by slug is strictly idempotent and unfollowing cleans up gracefully.
    """
    now = datetime.now(timezone.utc)
    user = User(
        name="Idempotency User",
        email=f"idemp_{int(now.timestamp())}@example.com",
        status="active",
    )
    db_session.add(user)
    await db_session.flush()

    source = await get_or_create_source(
        db_session,
        slug=f"source-idemp-{int(now.timestamp())}",
        name=f"Idemp Source {int(now.timestamp())}",
        url=f"https://idemp-{int(now.timestamp())}.com/rss",
    )

    service = PersonalizationService(db_session)

    # Follow 1st time by slug
    res1 = await service.follow_source(user.id, source.slug)
    assert res1 is True

    # Follow 2nd time by slug (idempotent)
    res2 = await service.follow_source(user.id, source.slug)
    assert res2 is True

    # Verify only 1 record in DB
    follow_records = (await db_session.execute(
        select(FollowedSource).where(FollowedSource.user_id == user.id, FollowedSource.source_id == source.id)
    )).scalars().all()
    assert len(follow_records) == 1

    # Unfollow by slug
    res3 = await service.unfollow_source(user.id, source.slug)
    assert res3 is False

    # Verify 0 records in DB
    follow_records = (await db_session.execute(
        select(FollowedSource).where(FollowedSource.user_id == user.id, FollowedSource.source_id == source.id)
    )).scalars().all()
    assert len(follow_records) == 0

    # Unfollow again (idempotent no-op)
    res4 = await service.unfollow_source(user.id, source.slug)
    assert res4 is False


@pytest.mark.asyncio
async def test_source_lifecycle_exclusion(db_session, cleanup_sources_test_data):
    """
    Test that disabled or deleted sources automatically stop delivering articles in Following feed.
    """
    now = datetime.now(timezone.utc)
    user = User(
        name="Lifecycle User",
        email=f"lifecycle_{int(now.timestamp())}@example.com",
        status="active",
    )
    db_session.add(user)

    test_source = await get_or_create_source(
        db_session,
        slug=f"ephemeral-{int(now.timestamp())}",
        name=f"Ephemeral Source {int(now.timestamp())}",
        url=f"https://ephemeral-{int(now.timestamp())}.com/rss",
    )

    art_id = 888003
    proc = ProcessedArticle(
        id=art_id,
        source_id=test_source.id,
        category_id=1,
        title="Ephemeral Announcement",
        slug=f"ephemeral-announcement-{int(now.timestamp())}",
        summary="A temporary announcement.",
        content="Full content...",
        source=test_source.name,
        editorial_status="APPROVED",
        publication_status="PUBLISHED",
        published_at=now,
        is_test_data=False,
    )
    read = ArticleReadModel(
        id=str(art_id),
        slug=proc.slug,
        url=f"https://ephemeral.com/article-{art_id}",
        title=proc.title,
        summary=proc.summary,
        content=proc.content,
        source=test_source.name,
        editorial_status="APPROVED",
        publication_status="PUBLISHED",
        published_at=proc.published_at,
        hash=f"hash-{art_id}",
        is_test_data=False,
    )
    db_session.add_all([proc, read])
    await db_session.commit()

    service = PersonalizationService(db_session)
    await service.follow_source(user.id, test_source.slug)

    # Feed while enabled: contains article
    feed = await service.get_source_following_feed(user.id)
    assert str(art_id) in [a.id for a in feed["items"]]

    # Disable source
    test_source.enabled = False
    await db_session.commit()

    # Feed while disabled: excludes article
    feed_disabled = await service.get_source_following_feed(user.id)
    assert str(art_id) not in [a.id for a in feed_disabled["items"]]
    assert feed_disabled["followed_sources_count"] == 0

    # Public list_sources excludes disabled source
    sources_list = await service.list_sources(user.id)
    assert test_source.slug not in [s["slug"] for s in sources_list]


@pytest.mark.asyncio
async def test_guest_sync_and_feed(db_session, cleanup_sources_test_data):
    """
    Test guest following with source_slugs query parameter and login sync.
    """
    now = datetime.now(timezone.utc)
    user = User(
        name="Guest Sync User",
        email=f"guest_sync_{int(now.timestamp())}@example.com",
        status="active",
    )
    db_session.add(user)
    await db_session.flush()

    s1 = await get_or_create_source(
        db_session,
        slug=f"guest-s1-{int(now.timestamp())}",
        name=f"Guest S1 {int(now.timestamp())}",
        url=f"https://guests1-{int(now.timestamp())}.com/rss",
    )
    s2 = await get_or_create_source(
        db_session,
        slug=f"guest-s2-{int(now.timestamp())}",
        name=f"Guest S2 {int(now.timestamp())}",
        url=f"https://guests2-{int(now.timestamp())}.com/rss",
    )
    active_slugs = [s1.slug, s2.slug]

    service = PersonalizationService(db_session)

    # 1. Guest feed query using source_slugs
    guest_feed = await service.get_source_following_feed(guest_source_slugs=active_slugs)
    assert guest_feed["followed_sources_count"] == len(active_slugs)

    # 2. Login sync merges guest follows into user's DB records
    synced_slugs = await service.sync_guest_follows(user.id, source_slugs=active_slugs)
    for slug in active_slugs:
        assert slug in synced_slugs

    # 3. Authenticated feed returns articles from the merged follows
    auth_feed = await service.get_source_following_feed(user_id=user.id)
    assert auth_feed["followed_sources_count"] == len(active_slugs)
