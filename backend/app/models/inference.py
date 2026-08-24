"""
AI Inference Record — Immutable provenance for AI-derived data.

This model captures the forensic evidence of each AI inference operation.
It is append-only: the fields provider, model, prompt_version, prompt_hash,
input_fingerprint, and source_article_id are NEVER updated after creation.

Cardinality: Article 1 → N AIInferenceRecord
Linkage: ArticleEntityLink.inference_id and RelationshipEdge.inference_id
         point to the specific inference that produced the relationship.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AIInferenceRecord(Base):
    """
    Immutable forensic record of an AI inference operation.

    Append-only contract: the following columns are NEVER updated:
      - provider, model, task_type
      - prompt_version, prompt_hash
      - input_fingerprint, source_article_id

    This record is evidence, not mutable configuration.
    Combined with ArticleEntityLink.inference_id, the full provenance
    chain is reconstructible:

        Article → AIInferenceRecord → provider/model/prompt → Entity/Relationship
    """
    __tablename__ = "ai_inference_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Source article — one article can have N inference records
    source_article_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("processed_articles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # AI provider identity
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False)

    # Task classification
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Prompt identity (immutable after creation)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Content identity — fingerprint of the input text
    input_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=True, index=True,
    )

    # Link to the detailed job telemetry record (optional)
    job_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ai_job_history.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Creation timestamp — never updated
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now,
    )

    # Relationships
    source_article = relationship("ProcessedArticle", foreign_keys=[source_article_id])
    job = relationship("AIJobHistory", foreign_keys=[job_id])
