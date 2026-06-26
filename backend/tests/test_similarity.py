import pytest

from app.ai.similarity import find_similar_articles
from app.models.article import ProcessedArticle
from app.models.source import Source  # noqa: F401


@pytest.mark.asyncio
async def test_find_similar_articles(db_session):
    from app.models.article import Category
    import uuid

    # Explicitly seed the required category to avoid FK violations on clean databases
    cat = Category(id=1, name="Test Category", slug=f"test-cat-{uuid.uuid4().hex[:6]}")
    db_session.add(cat)
    await db_session.commit()

    # Insert 3 articles with specific embeddings
    dim = 1536
    v1 = [1.0] + [0.0] * (dim - 1)
    v2 = [0.9] + [0.1] + [0.0] * (dim - 2)  # similar to v1
    v3 = [0.0] + [1.0] + [0.0] * (dim - 2)  # not similar to v1

    import uuid

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
        embedding=v2,
        embedding_status="completed",
    )
    art3 = ProcessedArticle(
        title="Article 3",
        slug=f"art-3-{suffix}",
        summary="S3",
        content="C3",
        source="S",
        category_id=1,
        published_status="published",
        embedding=v3,
        embedding_status="completed",
    )
    db_session.add_all([art1, art2, art3])
    await db_session.commit()

    # Test
    similar = await find_similar_articles(db_session, art1.id, limit=10, threshold=0.1)

    assert len(similar) == 1
    assert similar[0][0].id == art2.id
    assert similar[0][1] > 0.8  # cosine similarity should be high
