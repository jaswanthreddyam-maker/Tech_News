from datetime import datetime, timedelta, timezone

from app.ai.ranking import rank_semantic_results
from app.models.article import ProcessedArticle


def test_hybrid_ranker():
    now = datetime.now(timezone.utc)

    art1 = ProcessedArticle(
        title="Apple AI chip", summary="Apple announced a new AI chip today.", published_at=now - timedelta(days=1)
    )

    art2 = ProcessedArticle(
        title="Microsoft Azure AI",
        summary="Microsoft scales up Azure AI compute.",
        published_at=now - timedelta(days=30),
    )

    # Semantic matches from similarity engine
    # art1: semantic=0.9
    # art2: semantic=0.85
    matches = [(art1, 0.90), (art2, 0.85)]

    query = "Apple AI"
    ranked = rank_semantic_results(query, matches)

    assert len(ranked) == 2
    # art1 should be ranked higher due to keyword overlap, better semantic, and better freshness
    assert ranked[0]["article"] == art1
    assert ranked[1]["article"] == art2

    art1_score = ranked[0]["final_score"]
    art2_score = ranked[1]["final_score"]
    assert art1_score > art2_score

    # Check components
    assert ranked[0]["components"]["semantic"] == 0.90
    assert ranked[0]["components"]["freshness"] > 0.8  # ~1 day old
    assert ranked[1]["components"]["freshness"] < 0.3  # ~30 days old
