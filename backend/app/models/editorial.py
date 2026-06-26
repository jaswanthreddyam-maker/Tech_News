import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def utc_now():
    return datetime.now(timezone.utc)

class EditorialDraftStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    READY = "READY"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

class EditorialPatchStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"
    DISMISSED = "DISMISSED"
    VALID = "VALID"
    STALE = "STALE"
    CONFLICTED = "CONFLICTED"
    OBSOLETE = "OBSOLETE"

class EditorialDraft(Base):
    __tablename__ = "editorial_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False, default="ARTICLE") # ARTICLE, NEWSLETTER, PODCAST
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default=EditorialDraftStatus.DRAFT.value, index=True)

    category: Mapped[str] = mapped_column(String(100), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    author_id: Mapped[str] = mapped_column(String(255), nullable=True)

    # Audit fields
    scheduled_by: Mapped[str] = mapped_column(String(255), nullable=True)
    approved_by: Mapped[str] = mapped_column(String(255), nullable=True)
    published_by: Mapped[str] = mapped_column(String(255), nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(255), nullable=True)
    fact_checked_by: Mapped[str] = mapped_column(String(255), nullable=True)
    last_modified_by: Mapped[str] = mapped_column(String(255), nullable=True)

    publish_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    versions = relationship("DraftVersion", back_populates="draft", cascade="all, delete-orphan", order_by="DraftVersion.version")
    reviews = relationship("EditorialReviewArtifact", back_populates="draft", cascade="all, delete-orphan")
    decisions = relationship("EditorialDecision", back_populates="draft", cascade="all, delete-orphan", order_by="EditorialDecision.timestamp")
    threads = relationship("DiscussionThread", back_populates="draft", cascade="all, delete-orphan")
    sessions = relationship("EditorialSession", back_populates="draft", cascade="all, delete-orphan")
    workspace = relationship("Workspace", back_populates="drafts")
    distribution_configuration = relationship("DistributionConfiguration", back_populates="draft", uselist=False, cascade="all, delete-orphan")

class DistributionConfiguration(Base):
    __tablename__ = "distribution_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    draft_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("editorial_drafts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    audience_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True) # Soft link to Audience

    subject_template: Mapped[str] = mapped_column(String(255), nullable=True)
    preheader: Mapped[str] = mapped_column(String(255), nullable=True)
    from_name: Mapped[str] = mapped_column(String(100), nullable=True)
    reply_to: Mapped[str] = mapped_column(String(255), nullable=True)
    template_id: Mapped[str] = mapped_column(String(100), nullable=True)

    tracking_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    utm_campaign: Mapped[str] = mapped_column(String(100), nullable=True)
    send_as_digest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    personalization_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    draft = relationship("EditorialDraft", back_populates="distribution_configuration")


class EditorialDecision(Base):
    __tablename__ = "editorial_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    draft_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("editorial_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    decision_source: Mapped[str] = mapped_column(String(100), nullable=True) # Human, AI, Scheduler, System
    reason: Mapped[str] = mapped_column(Text, nullable=True)

    decision_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True) # duration, previous_state, new_state, etc.
    evidence: Mapped[list[dict]] = mapped_column(JSONB, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    draft = relationship("EditorialDraft", back_populates="decisions")


class DiscussionThread(Base):
    __tablename__ = "editorial_discussion_threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    draft_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("editorial_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    anchor: Mapped[dict] = mapped_column(JSONB, nullable=True) # {block_id, start, end, checksum}

    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    closed_by: Mapped[str] = mapped_column(String(255), nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    draft = relationship("EditorialDraft", back_populates="threads")
    comments = relationship("DraftComment", back_populates="thread", cascade="all, delete-orphan", order_by="DraftComment.timestamp")


class DraftComment(Base):
    __tablename__ = "editorial_draft_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    thread_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("editorial_discussion_threads.id", ondelete="CASCADE"), nullable=False, index=True
    )

    author_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    thread = relationship("DiscussionThread", back_populates="comments")


class DraftVersion(Base):
    __tablename__ = "editorial_draft_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    draft_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("editorial_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    editor_id: Mapped[str] = mapped_column(String(255), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=True)
    subtitle: Mapped[str] = mapped_column(String(255), nullable=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=True)

    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False) # Markdown
    rendered_html: Mapped[str] = mapped_column(Text, nullable=True)

    cover_image: Mapped[str] = mapped_column(Text, nullable=True)
    editor_notes: Mapped[str] = mapped_column(Text, nullable=True)

    category: Mapped[str] = mapped_column(String(100), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=True)
    metadata_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=True)
    seo: Mapped[dict] = mapped_column(JSONB, nullable=True)
    publishing_settings: Mapped[dict] = mapped_column(JSONB, nullable=True)
    ai_review_ids: Mapped[list[int]] = mapped_column(JSONB, nullable=True)

    environment: Mapped[dict] = mapped_column(JSONB, nullable=True) # ai_model, prompt_version, artifact_version, knowledge_version

    change_summary: Mapped[str] = mapped_column(Text, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    draft = relationship("EditorialDraft", back_populates="versions")


class EditorialReviewArtifact(Base):
    __tablename__ = "editorial_review_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    draft_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("editorial_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    reviewer_id: Mapped[str] = mapped_column(String(255), nullable=True)

    review_sections: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    quality_score: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    draft = relationship("EditorialDraft", back_populates="reviews")
    patches = relationship("EditorialPatch", back_populates="review", cascade="all, delete-orphan")


class EditorialPatch(Base):
    __tablename__ = "editorial_patches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    review_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("editorial_review_artifacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_type: Mapped[str] = mapped_column(String(100), nullable=False) # e.g. GRAMMAR, STYLE (now strings, not Enum)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=EditorialPatchStatus.PENDING.value)

    author: Mapped[dict] = mapped_column(JSONB, nullable=True) # {"type": "AI_MODEL", "identifier": "gpt-5.5"}

    confidence: Mapped[float] = mapped_column(Float, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=True)

    operations: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    evidence: Mapped[list[dict]] = mapped_column(JSONB, nullable=True)

    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by: Mapped[str] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    review = relationship("EditorialReviewArtifact", back_populates="patches")


class PublicationRecord(Base):
    __tablename__ = "publication_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    article_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    published_by: Mapped[str] = mapped_column(String(255), nullable=False)

    configuration_version: Mapped[str] = mapped_column(String(50), nullable=True)
    knowledge_version: Mapped[str] = mapped_column(String(50), nullable=True)
    review_version: Mapped[str] = mapped_column(String(50), nullable=True)
    distribution_version: Mapped[str] = mapped_column(String(50), nullable=True)

    distribution_summary: Mapped[dict] = mapped_column(JSONB, nullable=True) # e.g. {"RSS": "SUCCESS", "Sitemap": "SUCCESS"}

    distribution_manifest = relationship("DistributionManifest", back_populates="publication_record", uselist=False)

class EditorialSession(Base):
    __tablename__ = "editorial_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    draft_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("editorial_drafts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    editor_id: Mapped[str] = mapped_column(String(255), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    actions_summary: Mapped[dict] = mapped_column(JSONB, nullable=True) # e.g. {"patches_accepted": 5, "comments_added": 2}

    draft = relationship("EditorialDraft", back_populates="sessions")
