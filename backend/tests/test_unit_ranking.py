from datetime import datetime, timedelta, timezone

from app.services.ranking.news_ranking_engine import (
    calculate_engagement_score,
    calculate_final_score,
    calculate_freshness_score,
    calculate_impact_score,
)


def test_calculate_impact_score():
    # 1. Base score is 40.0
    # No keywords -> score is 40.0 (but wait, check category boosts or reductions)
    score_base = calculate_impact_score(title="Simple News Title", category="General", content="Nothing important.")
    assert score_base == 40.0

    # 2. Company boost: settings.RANKING_COMPANY_WEIGHTS has e.g. "openai" -> 30.0
    score_company = calculate_impact_score(
        title="OpenAI announces new update", category="General", content="Some text."
    )
    assert score_company == 40.0 + 30.0

    # 3. Tech keyword boost: settings.RANKING_TECH_KEYWORDS has "cybersecurity" -> 20.0
    score_tech = calculate_impact_score(
        title="Security check", category="General", content="A cybersecurity system details."
    )
    assert score_tech == 40.0 + 20.0

    # 4. Category Boost: "intelligence", "ai", "cybersecurity", "security" in category name -> +10.0
    score_category = calculate_impact_score(
        title="Simple Title", category="Artificial Intelligence", content="Normal content."
    )
    assert score_category == 40.0 + 10.0

    # 5. Reductions: settings.RANKING_REDUCTIONS has e.g. "minor update" -> -15.0
    score_reduction = calculate_impact_score(title="Minor update to system", category="General", content="Details.")
    assert score_reduction == 40.0 - 15.0

    # 6. Min/max bounds [0.0, 100.0]
    score_underflow = calculate_impact_score(
        title="Minor update blog post funding round", category="General", content=""
    )
    assert score_underflow == 0.0


def test_calculate_freshness_score():
    now = datetime.now(timezone.utc)

    # 0-2 Hours = 100.0
    assert calculate_freshness_score(now - timedelta(hours=1)) == 100.0
    # 2-6 Hours = 80.0
    assert calculate_freshness_score(now - timedelta(hours=3)) == 80.0
    # 6-12 Hours = 60.0
    assert calculate_freshness_score(now - timedelta(hours=8)) == 60.0
    # 12-18 Hours = 40.0
    assert calculate_freshness_score(now - timedelta(hours=14)) == 40.0
    # 18-24 Hours = 20.0
    assert calculate_freshness_score(now - timedelta(hours=20)) == 20.0
    # 24+ Hours = 0.0
    assert calculate_freshness_score(now - timedelta(hours=26)) == 0.0
    # Future = 100.0
    assert calculate_freshness_score(now + timedelta(hours=2)) == 100.0


def test_calculate_engagement_score():
    # Baseline: source credibility weight is 40% (e.g. cred=80 -> baseline=32.0)
    # Metadata score adds up to 60%
    assert calculate_engagement_score(metadata_str=None, source_credibility=80) == 32.0

    # Social: reddit_score + (hn_score * 1.5) + (mentions * 5.0), divided by 10.0, max 60.0 points
    # Reddit = 100, HN = 100 (150 pts), Mentions = 10 (50 pts) -> total social = 300 pts -> 30 points contribution
    meta_json = '{"reddit_score": 100, "hn_score": 100, "mentions": 10}'
    score_engagement = calculate_engagement_score(metadata_str=meta_json, source_credibility=80)
    assert score_engagement == 32.0 + 30.0

    # Underflow/Overflow bounds
    large_meta = '{"reddit_score": 10000}'
    assert calculate_engagement_score(metadata_str=large_meta, source_credibility=100) == 100.0  # capped at 100


def test_calculate_final_score():
    # Formula: impact * 0.60 + freshness * 0.25 + engagement * 0.15
    res = calculate_final_score(impact=50.0, freshness=100.0, engagement=80.0)
    expected = (50.0 * 0.60) + (100.0 * 0.25) + (80.0 * 0.15)
    assert res == expected
