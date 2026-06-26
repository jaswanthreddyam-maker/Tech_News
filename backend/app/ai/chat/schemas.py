from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel


class ConversationMode(str, Enum):
    GENERAL = "GENERAL"
    ARTICLE = "ARTICLE"
    COMPARISON = "COMPARISON"
    ELI15 = "ELI15"
    TIMELINE = "TIMELINE"
    DIGEST = "DIGEST"
    TOPIC = "TOPIC"
    WORKSPACE = "WORKSPACE"
    WORKSPACE_DIGEST = "WORKSPACE_DIGEST"


class OwnerType(str, Enum):
    USER = "user"
    ANONYMOUS = "anonymous"


class ChatRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str
    name: str | None = None
    evidence: "EvidenceBundle | None" = None


class Citation(BaseModel):
    article_id: int
    title: str
    url: str | None = None
    paragraph: str | None = None
    score: float
    confidence: str | None = None  # "High", "Medium", "Low" derived from score


class ConversationMetadata(BaseModel):
    """Metadata stored alongside each conversation in Redis."""

    conversation_id: str
    title: str = "New Conversation"
    mode: ConversationMode = ConversationMode.GENERAL
    owner_type: OwnerType = OwnerType.ANONYMOUS
    owner_id: str = ""
    article_id: int | None = None
    workspace_id: int | None = None
    topic: str | None = None
    message_count: int = 0
    last_model: str = ""
    created_at: str = ""  # ISO timestamp
    updated_at: str = ""  # ISO timestamp


class StreamEventType(str, Enum):
    RETRIEVAL_STARTED = "retrieval_started"
    RETRIEVAL_FINISHED = "retrieval_finished"
    PROVENANCE = "provenance"
    EVIDENCE_BUNDLE = "evidence_bundle"
    COMPARISON_METADATA = "comparison_metadata"
    GENERATION_STARTED = "generation_started"
    TOKEN = "token"
    CITATION = "citation"
    SUGGESTED_FOLLOW_UPS = "suggested_follow_ups"
    TITLE_GENERATED = "title_generated"
    COMPLETED = "completed"
    ERROR = "error"


class StreamEvent(BaseModel):
    event: StreamEventType
    data: dict[str, Any]


class ComparisonContext(BaseModel):
    type: Literal["query", "article", "topic", "company", "product", "timespan"]
    value: str


class ProvenanceItem(BaseModel):
    type: Literal["article", "note", "comparison", "conversation"]
    id: str | int
    title: str | None = None
    url: str | None = None


class ProvenanceSummary(BaseModel):
    articles: int = 0
    notes: int = 0
    comparisons: int = 0
    conversations: int = 0


class ProvenanceData(BaseModel):
    summary: ProvenanceSummary
    items: list[ProvenanceItem]
    confidence: str | None = None  # "High", "Medium", "Low"

class EvidenceItem(BaseModel):
    id: str | int
    type: Literal["article", "entity", "topic", "timeline_event", "relationship", "note", "comparison", "conversation"]
    title: str | None = None
    url: str | None = None
    description: str | None = None
    score: float | None = None

class EvidenceBundle(BaseModel):
    items: list[EvidenceItem] = []
    confidence: str | None = None
