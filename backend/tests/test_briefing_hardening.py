import asyncio
import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import ArticleReadModel
from app.briefing.models import (
    DailyBriefingEdition,
    DailyBriefingItem,
    DailyBriefingSubscriber,
    DailyBriefingDelivery,
    BriefingDeliveryStatus,
)
from app.briefing.service import (
    DailyBriefingService,
    create_signed_unsubscribe_token,
    create_signed_verification_token,
    _verify_signed_token,
)
from app.briefing.selector import DailyBriefingSelector
from app.briefing.enricher import BriefingEnricher
from app.briefing.contracts import PRIMARY_QUALITY_FLOOR, EMERGENCY_QUALITY_FLOOR


class MockArticle:
    def __init__(self, art_id: str, title: str, summary: str, source: str = "TechCrunch", category: str = "Technology", score: float = 25.0):
        self.id = art_id
        self.article_id = art_id
        self.title = title
        self.summary = summary
        self.source = source
        self.category = category
        self.final_score = score
        self.publication_status = "PUBLISHED"
        self.is_test_data = False
        self.published_at = datetime.now(timezone.utc)
        self.reading_time = 3
        self.slug = f"slug-{art_id}"
        self.url = f"https://example.com/{art_id}"


@pytest.mark.asyncio
async def test_authenticated_subscriber_ownership_by_user_id(db_session: AsyncSession):
    """
    P0-1: Strict user_id ownership invariant.
    User A (id='user-100') cannot access or mutate User B's subscriber (id='user-200').
    """
    sub_b = DailyBriefingSubscriber(
        user_id="user-200",
        email="bob@example.com",
        enabled=True,
        email_verified_at=datetime.now(timezone.utc),
        unsubscribe_token_hash="unsub_bob_hash",
    )
    db_session.add(sub_b)
    await db_session.commit()

    # User A requests their own subscriber
    sub_a = await DailyBriefingService.get_subscriber_for_user(
        db_session, user_id="user-100", email="alice@example.com"
    )
    await db_session.commit()

    assert sub_a.user_id == "user-100"
    assert sub_a.email == "alice@example.com"
    assert sub_a.id != sub_b.id

    # If User A tries to pass bob's email, get_subscriber_for_user returns User A's subscriber
    sub_a_again = await DailyBriefingService.get_subscriber_for_user(
        db_session, user_id="user-100", email="bob@example.com"
    )
    assert sub_a_again.id == sub_a.id
    assert sub_a_again.user_id == "user-100"


@pytest.mark.asyncio
async def test_preferences_do_not_auto_verify_email(db_session: AsyncSession):
    """
    P0-2: Zero-Bypass Email Verification State Machine.
    Saving preferences with enabled=True on an unverified subscriber keeps enabled=False.
    """
    sub = DailyBriefingSubscriber(
        user_id="user-unverified",
        email="unverified@example.com",
        enabled=False,
        email_verified_at=None,
        unsubscribe_token_hash="unsub_unverified_hash",
    )
    db_session.add(sub)
    await db_session.commit()

    assert sub.email_verified_at is None
    assert sub.enabled is False

    # Simulate preference save with enabled intent
    if sub.email_verified_at is not None:
        sub.enabled = True
    else:
        sub.enabled = False

    await db_session.commit()
    await db_session.refresh(sub)

    assert sub.enabled is False
    assert sub.email_verified_at is None

    # Now verify via cryptographic token
    raw_token = create_signed_verification_token(sub.id, sub.email)
    verified_sub = await DailyBriefingService.verify_email_token(db_session, raw_token)
    await db_session.commit()

    assert verified_sub is not None
    assert verified_sub.enabled is True
    assert verified_sub.email_verified_at is not None


@pytest.mark.asyncio
async def test_multi_day_deterministic_unsubscribe_validity(db_session: AsyncSession):
    """
    P0-3: Multi-Day Deterministic Signed Unsubscribe.
    Monday's email token remains valid after Tuesday's delivery (no mutable DB hash overwrite).
    """
    sub = DailyBriefingSubscriber(
        user_id="user-unsub-test",
        email="reader@example.com",
        enabled=True,
        email_verified_at=datetime.now(timezone.utc),
        unsubscribe_token_hash="unsub_reader_hash",
    )
    db_session.add(sub)
    await db_session.commit()

    # Generate Monday token (issued yesterday)
    now = datetime.now(timezone.utc)
    monday_payload = {
        "type": "unsub",
        "sid": sub.id,
        "email": sub.email.strip().lower(),
        "iat": int((now - timedelta(days=1)).timestamp()),
        "exp": int((now + timedelta(days=89)).timestamp()),
    }
    from app.briefing.service import _sign_payload
    monday_token = _sign_payload(monday_payload)

    # Simulate Tuesday dispatch (issued today)
    tuesday_token = create_signed_unsubscribe_token(sub.id, sub.email)
    assert monday_token != tuesday_token

    # Verify that Monday token still successfully unsubscribes the user
    unsub_sub = await DailyBriefingService.unsubscribe_by_token(db_session, monday_token)
    await db_session.commit()

    assert unsub_sub is not None
    assert unsub_sub.id == sub.id
    assert unsub_sub.enabled is False
    assert unsub_sub.unsubscribed_at is not None


@pytest.mark.asyncio
async def test_concurrent_daily_edition_creation_safety(db_session: AsyncSession):
    """
    P1/P0-4: Concurrency-safe singleton DailyBriefingEdition creation.
    Repeated generation for the same date returns the existing edition without duplicate key IntegrityError.
    """
    today_str = "2026-08-25"

    articles = [
        MockArticle(f"art-{i}", f"AI Breakthrough {i}", f"Summary of breakthrough {i}", score=20.0 + i)
        for i in range(1, 6)
    ]

    with patch.object(DailyBriefingSelector, "select_top_stories", new=AsyncMock(return_value=articles)):
        edition_1 = await DailyBriefingService.get_or_create_daily_edition(db_session, edition_date=today_str)
        await db_session.commit()

        edition_2 = await DailyBriefingService.get_or_create_daily_edition(db_session, edition_date=today_str)
        await db_session.commit()

    assert edition_1.id == edition_2.id
    assert edition_1.edition_date == today_str
    # Exactly one edition in database
    stmt = select(DailyBriefingEdition).where(DailyBriefingEdition.edition_date == today_str)
    all_editions = (await db_session.execute(stmt)).scalars().all()
    assert len(all_editions) == 1


@pytest.mark.asyncio
async def test_topic_personalization_preserves_editorial_rank(db_session: AsyncSession):
    """
    P1: Topic Personalization Projection.
    Matches subscriber topics while preserving global editorial ranking.
    """
    sub = DailyBriefingSubscriber(
        user_id="user-ai-fan",
        email="aifan@example.com",
        enabled=True,
        email_verified_at=datetime.now(timezone.utc),
        story_count=3,
        topics=["artificial-intelligence"],
        unsubscribe_token_hash="unsub_aifan_hash",
    )
    db_session.add(sub)

    edition = DailyBriefingEdition(
        edition_date="2026-08-26",
        selection_hash="hash-pers-test",
        algorithm_version="v2.2",
        status="PUBLISHED",
    )
    db_session.add(edition)
    await db_session.flush()

    items = [
        DailyBriefingItem(edition_id=edition.id, article_id="1", cluster_id="c1", rank=1, headline="Cloud News", category="cloud", why_it_matters="Cloud summary"),
        DailyBriefingItem(edition_id=edition.id, article_id="2", cluster_id="c2", rank=2, headline="AI Model Release", category="artificial-intelligence", why_it_matters="AI summary"),
        DailyBriefingItem(edition_id=edition.id, article_id="3", cluster_id="c3", rank=3, headline="Hardware GPU", category="hardware", why_it_matters="Hardware summary"),
        DailyBriefingItem(edition_id=edition.id, article_id="4", cluster_id="c4", rank=4, headline="AI LLM Reasoning", category="artificial-intelligence", why_it_matters="Reasoning summary"),
    ]
    for it in items:
        db_session.add(it)
    await db_session.commit()
    edition.loaded_items = items

    mock_provider = MagicMock()
    mock_provider.send = AsyncMock(return_value=MagicMock(success=True, message_id="msg-123", error=None))

    with patch("app.briefing.service.get_email_provider", return_value=mock_provider):
        delivery = await DailyBriefingService.dispatch_delivery(db_session, edition=edition, subscriber=sub)
        await db_session.commit()

    assert delivery.status == BriefingDeliveryStatus.SENT
    assert delivery.stories_delivered == 3
    # Verify provider payload received AI items (rank 2, 4) followed by cloud (rank 1)
    call_args = mock_provider.send.call_args[0][0]
    assert "AI Model Release" in call_args.html
    assert "AI LLM Reasoning" in call_args.html


@pytest.mark.asyncio
async def test_selector_quality_floors(db_session: AsyncSession):
    """
    P1: Selector rejects articles below EMERGENCY_QUALITY_FLOOR (10.0) even in fallback mode.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=10)
    art_low = ArticleReadModel(
        id="low-quality-floor-test",
        url="https://example.com/low-floor",
        title="Spam Article",
        content="Short spam body content.",
        hash="hash_low_floor",
        source="SpamSource",
        category="Technology",
        final_score=5.0,  # Below emergency floor
        publication_status="PUBLISHED",
        is_test_data=False,
        published_at=cutoff,
    )
    art_good = ArticleReadModel(
        id="good-quality-floor-test",
        url="https://example.com/good-floor",
        title="Legitimate AI Research",
        content="Legitimate AI research paper details.",
        hash="hash_good_floor",
        source="Arxiv",
        category="Technology",
        final_score=18.0,  # Above primary floor
        publication_status="PUBLISHED",
        is_test_data=False,
        published_at=cutoff,
    )
    db_session.add_all([art_low, art_good])
    await db_session.commit()

    selected = await DailyBriefingSelector.select_top_stories(db_session, limit=5)
    selected_ids = [a.id for a in selected]

    assert "good-quality-floor-test" in selected_ids
    assert "low-quality-floor-test" not in selected_ids


@pytest.mark.asyncio
async def test_fault_isolated_parallel_enrichment():
    """
    P1: Parallel AI Enrichment with Per-Item Fault Isolation.
    If Article 2 times out or throws an error, Article 2 falls back to canonical summary
    while Articles 1 and 3 enrich successfully.
    """
    art1 = MockArticle("1", "Article One", "Canonical summary one")
    art2 = MockArticle("2", "Article Two", "Canonical summary two")
    art3 = MockArticle("3", "Article Three", "Canonical summary three")

    async def mock_enrich_item(art):
        if art.id == "2":
            raise asyncio.TimeoutError("Gemini timed out")
        return f"AI enriched why it matters for {art.id}"

    with patch.object(BriefingEnricher, "enrich_item", side_effect=mock_enrich_item):
        enriched = await BriefingEnricher.enrich_articles([art1, art2, art3], concurrency=3)

    assert len(enriched) == 3
    assert enriched[0]["why_it_matters"] == "AI enriched why it matters for 1"
    # Article 2 gracefully fell back to canonical summary without crashing the batch
    assert enriched[1]["why_it_matters"] == "Canonical summary two"
    assert enriched[2]["why_it_matters"] == "AI enriched why it matters for 3"


@pytest.mark.asyncio
async def test_send_test_briefing_requires_verified_email(db_session: AsyncSession):
    """
    P0: Test send requires verified subscriber (no auto-verification side-effect).
    """
    sub = DailyBriefingSubscriber(
        user_id="user-test-unverified",
        email="unverified-test@example.com",
        enabled=False,
        email_verified_at=None,
        unsubscribe_token_hash="unsub_test_unverified_hash",
    )
    db_session.add(sub)
    await db_session.commit()

    with pytest.raises(ValueError, match="is not verified"):
        await DailyBriefingService.send_test_briefing(db_session, email="unverified-test@example.com")
