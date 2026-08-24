"""
AI Provenance — Integration & Invariant Tests.

Tests the frozen Contract 5:
- Invariant: One AIInferenceRecord represents one immutable AI inference execution/result.
- Cardinality: Article 1 → N AIInferenceRecord.
- Linkage: ArticleEntityLink.inference_id and RelationshipEdge.inference_id
  point to the AIInferenceRecord that produced the graph artifacts.
"""
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.tnt.projectors import EntityProjector, RelationshipProjector
from app.models.article import ProcessedArticle
from app.models.inference import AIInferenceRecord
from app.models.tnt_knowledge import (
    ArticleEntityLink,
    EntityNode,
    RelationshipEdge,
)
from app.schemas.knowledge import Entity, EntityType, KnowledgeArtifact, Relationship, RelationshipPredicate

pytestmark = pytest.mark.asyncio


async def _create_test_article(db: AsyncSession) -> str:
    import uuid
    from app.models.article import ArticleReadModel

    art_id = f"art_{uuid.uuid4().hex[:12]}"
    arm = ArticleReadModel(
        id=art_id,
        url=f"http://test.com/prov-art-{art_id}",
        title=f"Prov Test Article {art_id}",
        content="Test article content for provenance verification.",
        source="TechCrunch",
        hash=f"hash_{art_id}",
        published_at=datetime.now(timezone.utc),
    )
    db.add(arm)
    await db.commit()
    return art_id


# ---------------------------------------------------------------------------
# Test 1: AIInferenceRecord Creation & Immutability Invariant
# ---------------------------------------------------------------------------

async def test_ai_inference_record_creation_and_attributes(db_session: AsyncSession):
    """
    Verify AIInferenceRecord can be persisted with full forensic evidence fields.
    """
    record = AIInferenceRecord(
        provider="google",
        model="gemini-2.0-flash",
        task_type="knowledge_extraction",
        prompt_version="1.0.0",
        prompt_hash="a1b2c3d4e5f67890",
        input_fingerprint="fp_test_article_123",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    assert record.id is not None
    assert record.provider == "google"
    assert record.model == "gemini-2.0-flash"
    assert record.prompt_version == "1.0.0"
    assert record.prompt_hash == "a1b2c3d4e5f67890"
    assert record.input_fingerprint == "fp_test_article_123"


# ---------------------------------------------------------------------------
# Test 2: EntityProjector Provenance Linkage
# ---------------------------------------------------------------------------

async def test_entity_projector_links_inference_record(db_session: AsyncSession):
    """
    Verify EntityProjector creates an AIInferenceRecord and populates inference_id
    on ArticleEntityLink.
    """
    artifact_id = await _create_test_article(db_session)

    artifact = KnowledgeArtifact(
        artifact_id=artifact_id,
        entities=[
            Entity(
                id="ent_google_quantum",
                canonical_name="Google Quantum AI",
                entity_type=EntityType.ORGANIZATION,
                confidence=0.95,
            )
        ],
        provider="google",
        model="gemini-2.0-flash",
        prompt_version="2.1.0",
        prompt_hash="hash_ent_extraction_v2",
        input_fingerprint="fp_article_quantum",
    )

    projector = EntityProjector()
    await projector.project(artifact, db_session)

    # Verify ArticleEntityLink has inference_id populated
    stmt = select(ArticleEntityLink).where(ArticleEntityLink.article_id == artifact_id)
    res = await db_session.execute(stmt)
    link = res.scalars().first()

    assert link is not None
    assert link.entity_id == "ent_google_quantum"
    assert link.inference_id is not None

    # Forensic traceability: load inference record
    inf_stmt = select(AIInferenceRecord).where(AIInferenceRecord.id == link.inference_id)
    inf_res = await db_session.execute(inf_stmt)
    inference = inf_res.scalar_one()

    assert inference.provider == "google"
    assert inference.model == "gemini-2.0-flash"
    assert inference.prompt_version == "2.1.0"
    assert inference.prompt_hash == "hash_ent_extraction_v2"


# ---------------------------------------------------------------------------
# Test 3: RelationshipProjector Provenance Linkage
# ---------------------------------------------------------------------------

async def test_relationship_projector_links_inference_record(db_session: AsyncSession):
    """
    Verify RelationshipProjector links RelationshipEdge to the AIInferenceRecord.
    """
    artifact_id = await _create_test_article(db_session)

    # Create entity nodes first
    ent_proj = EntityProjector()
    ent_artifact = KnowledgeArtifact(
        artifact_id=artifact_id,
        entities=[
            Entity(id="ent_deepmind", canonical_name="DeepMind", entity_type=EntityType.ORGANIZATION, confidence=0.9),
            Entity(id="ent_alphafold", canonical_name="AlphaFold", entity_type=EntityType.PRODUCT, confidence=0.95),
        ],
        provider="google",
        model="gemini-2.0-flash",
        prompt_version="1.0.0",
        prompt_hash="hash_entities",
    )
    await ent_proj.project(ent_artifact, db_session)

    # Now project relationship with provenance
    rel_artifact = KnowledgeArtifact(
        artifact_id=artifact_id,
        relationships=[
            Relationship(
                source="ent_deepmind",
                predicate=RelationshipPredicate.RELEASED,
                target="ent_alphafold",
                confidence=0.98,
            )
        ],
        provider="google",
        model="gemini-2.0-flash",
        prompt_version="1.1.0",
        prompt_hash="hash_rel_v1",
        input_fingerprint="fp_deepmind_alphafold",
    )

    rel_proj = RelationshipProjector()
    await rel_proj.project(rel_artifact, db_session)

    # Verify RelationshipEdge has inference_id populated
    stmt = select(RelationshipEdge).where(RelationshipEdge.article_id == artifact_id)
    res = await db_session.execute(stmt)
    edge = res.scalars().first()

    assert edge is not None
    assert edge.source_id == "ent_deepmind"
    assert edge.target_id == "ent_alphafold"
    assert edge.inference_id is not None

    # Forensic traceability
    inf_stmt = select(AIInferenceRecord).where(AIInferenceRecord.id == edge.inference_id)
    inf_res = await db_session.execute(inf_stmt)
    inference = inf_res.scalar_one()

    assert inference.prompt_hash == "hash_rel_v1"
    assert inference.task_type == "relationships"
