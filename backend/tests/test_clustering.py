import pytest

from app.ai.clustering import assign_to_cluster
from app.models.article import ProcessedArticle
from app.models.source import Source  # noqa: F401


@pytest.mark.asyncio
async def test_clustering_assignment(db_session):
    from app.models.article import Category
    import uuid

    # Explicitly seed the required category to avoid FK violations on clean databases
    cat = Category(id=1, name="Test Category", slug=f"test-cat-{uuid.uuid4().hex[:6]}")
    db_session.add(cat)
    await db_session.commit()

    # Insert 2 identical articles
    dim = 1536
    v1 = [1.0] + [0.0] * (dim - 1)

    suffix = uuid.uuid4().hex[:6]
    art1 = ProcessedArticle(
        title="Article 1",
        slug=f"art-1-{suffix}",
        summary="S1",
        content="C1",
        source="S",
        category_id=1,
        published_status="published",
        embedding=v1,
        embedding_status="completed",
    )
    art2 = ProcessedArticle(
        title="Article 2",
        slug=f"art-2-{suffix}",
        summary="S2",
        content="C2",
        source="S",
        category_id=1,
        published_status="published",
        embedding=v1,
        embedding_status="completed",
    )
    db_session.add_all([art1, art2])
    await db_session.commit()

    # 1. Cluster art1
    await assign_to_cluster(db_session, art1)
    assert art1.cluster_id is not None
    assert art1.cluster_score == 1.0

    # Commit changes
    await db_session.commit()

    # 2. Cluster art2
    await assign_to_cluster(db_session, art2)
    assert art2.cluster_id == art1.cluster_id
    assert art2.cluster_score > 0.9  # since vectors are identical
