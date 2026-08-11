import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
from sqlalchemy import select

from app.models.article import ArticleReadModel
from app.briefing.models import (
    DailyBriefingEdition, DailyBriefingItem, DailyBriefingSubscriber,
    DailyBriefingDelivery, BriefingDeliveryStatus
)
from app.briefing.service import DailyBriefingService


class MockArticle:
    def __init__(self, art_id: str, title: str, summary: str, source: str = "TechCrunch", category: str = "Technology"):
        self.id = art_id
        self.article_id = art_id
        self.title = title
        self.summary = summary
        self.source = source
        self.category = category
        self.url = f"https://example.com/{art_id}"
        self.source_url = self.url
        self.cluster_id = None
        self.read_time = 3
        self.reading_time = 3
        self.final_score = 85.0
        self.publication_status = "PUBLISHED"
        self.is_test_data = False
        self.published_at = datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_zero_eligible_articles_is_valid_editorial_outcome(db_session):
    """0 candidate articles yields an edition with 0 items without throwing exceptions."""
    edition_date = "2026-08-11"
    with patch("app.briefing.selector.DailyBriefingSelector.select_top_stories", new_callable=AsyncMock) as mock_select:
        mock_select.return_value = []
        edition = await DailyBriefingService.get_or_create_daily_edition(db_session, edition_date=edition_date)
        assert edition is not None
        assert edition.edition_date == edition_date
        assert len(edition.loaded_items) == 0
        assert edition.status == "EMPTY"


@pytest.mark.asyncio
async def test_empty_edition_does_not_poison_future_generation(db_session):
    """First run with 0 articles creates 0-item edition; second run after articles arrive populates stories."""
    edition_date = "2026-08-12"

    with patch("app.briefing.selector.DailyBriefingSelector.select_top_stories", new_callable=AsyncMock) as mock_select:
        # Run 1: 0 candidate articles
        mock_select.return_value = []
        edition1 = await DailyBriefingService.get_or_create_daily_edition(db_session, edition_date=edition_date)
        assert len(edition1.loaded_items) == 0

        # Run 2: Articles now available
        mock_select.return_value = [
            MockArticle("art_101", "Breaking Neural Architecture Released", "Major AI breakthrough.", "TechCrunch")
        ]
        edition2 = await DailyBriefingService.get_or_create_daily_edition(db_session, edition_date=edition_date)
        assert edition2.id == edition1.id
        assert len(edition2.loaded_items) == 1
        assert edition2.loaded_items[0].headline == "Breaking Neural Architecture Released"
        assert edition2.status == "PUBLISHED"


@pytest.mark.asyncio
async def test_existing_empty_unsent_edition_is_re_evaluated(db_session):
    """An existing unsent 0-item edition gets re-evaluated when candidate articles arrive."""
    edition_date = "2026-08-13"

    # Pre-insert an empty unsent edition
    empty_edition = DailyBriefingEdition(
        edition_date=edition_date,
        selection_hash="empty_hash",
        algorithm_version="v2.2",
        status="EMPTY",
    )
    db_session.add(empty_edition)
    await db_session.commit()

    with patch("app.briefing.selector.DailyBriefingSelector.select_top_stories", new_callable=AsyncMock) as mock_select:
        mock_select.return_value = [
            MockArticle("art_102", "Quantum Processor Reaches Commercial Milestone", "Quantum breakthrough.", "Ars Technica")
        ]
        edition = await DailyBriefingService.get_or_create_daily_edition(db_session, edition_date=edition_date)
        assert edition.id == empty_edition.id
        assert len(edition.loaded_items) == 1
        assert edition.status == "PUBLISHED"


@pytest.mark.asyncio
async def test_sent_edition_is_not_implicitly_regenerated(db_session):
    """An empty edition that HAS already been successfully sent remains an immutable historical snapshot."""
    edition_date = "2026-08-14"

    # Create empty edition with a SENT delivery record
    sent_edition = DailyBriefingEdition(
        edition_date=edition_date,
        selection_hash="sent_empty_hash",
        algorithm_version="v2.2",
        status="PUBLISHED",
    )
    db_session.add(sent_edition)
    await db_session.flush()

    sub = await DailyBriefingService.get_or_create_subscriber(db_session, email="historical_test@example.com")
    await db_session.flush()

    sent_delivery = DailyBriefingDelivery(
        edition_id=sent_edition.id,
        subscriber_id=sub.id,
        email=sub.email,
        status=BriefingDeliveryStatus.SENT,
        provider_message_id="msg_historical_123",
        stories_delivered=0,
    )
    db_session.add(sent_delivery)
    await db_session.commit()

    with patch("app.briefing.selector.DailyBriefingSelector.select_top_stories", new_callable=AsyncMock) as mock_select:
        mock_select.return_value = [
            MockArticle("art_103", "Late Story After Dispatch", "Arrived after send.", "The Verge")
        ]
        edition = await DailyBriefingService.get_or_create_daily_edition(db_session, edition_date=edition_date)
        assert edition.id == sent_edition.id
        assert len(edition.loaded_items) == 0
        # Ensure selector was NOT called because sent edition is immutable
        mock_select.assert_not_called()


@pytest.mark.asyncio
async def test_non_empty_edition_is_reused(db_session):
    """An existing non-empty edition is reused directly without re-querying selector."""
    edition_date = "2026-08-15"

    populated_edition = DailyBriefingEdition(
        edition_date=edition_date,
        selection_hash="populated_hash",
        algorithm_version="v2.2",
        status="PUBLISHED",
    )
    db_session.add(populated_edition)
    await db_session.flush()

    item = DailyBriefingItem(
        edition_id=populated_edition.id,
        article_id="art_existing_1",
        rank=1,
        headline="Existing Cached Headline",
        why_it_matters="Already generated and cached.",
        category="Artificial Intelligence",
        source="Wired",
        url="https://example.com/cached",
        read_time=3,
    )
    db_session.add(item)
    await db_session.commit()

    with patch("app.briefing.selector.DailyBriefingSelector.select_top_stories", new_callable=AsyncMock) as mock_select:
        edition = await DailyBriefingService.get_or_create_daily_edition(db_session, edition_date=edition_date)
        assert edition.id == populated_edition.id
        assert len(edition.loaded_items) == 1
        assert edition.loaded_items[0].headline == "Existing Cached Headline"
        mock_select.assert_not_called()
