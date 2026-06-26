from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DraftVersionResponse(BaseModel):
    id: int
    version: int
    editor_id: str | None
    title: str | None
    subtitle: str | None
    slug: str | None
    content_hash: str
    content: str
    rendered_html: str | None
    cover_image: str | None
    editor_notes: str | None
    category: str | None
    tags: list[str] | None
    metadata_snapshot: dict[str, Any] | None
    seo: dict[str, Any] | None
    publishing_settings: dict[str, Any] | None
    ai_review_ids: list[int] | None
    environment: dict[str, Any] | None
    change_summary: str | None
    timestamp: datetime

    class Config:
        orm_mode = True
        from_attributes = True

class EditorialPatchResponse(BaseModel):
    id: int
    review_id: int
    section_type: str
    status: str
    author: dict[str, Any] | None
    confidence: float | None
    reason: str | None
    operations: list[dict[str, Any]]
    evidence: list[dict[str, Any]] | None
    accepted_at: datetime | None
    accepted_by: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        from_attributes = True

class EditorialReviewResponse(BaseModel):
    id: int
    reviewer_id: str | None
    review_sections: list[dict[str, Any]]
    quality_score: float | None
    created_at: datetime
    patches: list[EditorialPatchResponse] = Field(default_factory=list)

    class Config:
        orm_mode = True
        from_attributes = True

class EditorialDraftBase(BaseModel):
    title: str | None = None
    content: str
    category: str | None = None
    tags: list[str] = Field(default_factory=list)

class EditorialDraftCreate(EditorialDraftBase):
    workspace_id: int
    author_id: str | None = None

class EditorialDraftUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    rendered_html: str | None = None
    seo: dict[str, Any] | None = None
    metadata_snapshot: dict[str, Any] | None = None
    cover_image: str | None = None
    environment: dict[str, Any] | None = None

    change_summary: str | None = None
    editor_id: str | None = None
    status: str | None = None

class ThreadCreate(BaseModel):
    anchor: dict[str, Any] | None = None
    content: str

class CommentCreate(BaseModel):
    content: str

class DraftCommentResponse(BaseModel):
    id: int
    thread_id: int
    author_id: str
    content: str
    timestamp: datetime

    class Config:
        orm_mode = True
        from_attributes = True

class DiscussionThreadResponse(BaseModel):
    id: int
    draft_id: int
    anchor: dict[str, Any] | None
    resolved: bool
    closed_by: str | None
    closed_at: datetime | None
    created_at: datetime
    comments: list[DraftCommentResponse] = Field(default_factory=list)

    class Config:
        orm_mode = True
        from_attributes = True

class PatchUpdate(BaseModel):
    status: str
    reason: str | None = None
    accepted_by: str | None = None

class PublicationRecordResponse(BaseModel):
    id: int
    article_id: str
    published_at: datetime
    published_by: str
    configuration_version: str | None
    knowledge_version: str | None
    review_version: str | None
    distribution_version: str | None
    distribution_summary: dict[str, Any] | None

    class Config:
        orm_mode = True
        from_attributes = True

class EditorialDraftResponse(EditorialDraftBase):
    id: int
    workspace_id: int
    status: str
    author_id: str | None = None

    scheduled_by: str | None
    approved_by: str | None
    published_by: str | None
    reviewed_by: str | None
    fact_checked_by: str | None
    last_modified_by: str | None
    publish_at: datetime | None

    created_at: datetime
    updated_at: datetime

    versions: list[DraftVersionResponse] = Field(default_factory=list)
    reviews: list[EditorialReviewResponse] = Field(default_factory=list)
    threads: list[DiscussionThreadResponse] = Field(default_factory=list)

    class Config:
        orm_mode = True
        from_attributes = True

class FactCheckResponse(BaseModel):
    claims_checked: list[dict[str, Any]]
    overall_status: str

class PublishResponse(BaseModel):
    status: str
    artifact_id: str
    message: str
