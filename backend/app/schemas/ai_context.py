from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PrivacyLevel(str, Enum):
    PUBLIC = "PUBLIC"           # Only article data.
    PERSONALIZED = "PERSONALIZED" # Article + User interests + Reading history.
    PRIVATE = "PRIVATE"         # Article only, no personalization.

class ContextProfile(str, Enum):
    SUMMARY = "SUMMARY"
    CHAT = "CHAT"
    TIMELINE = "TIMELINE"
    COMPARISON = "COMPARISON"
    RESEARCH = "RESEARCH"

class AIContextMetadata(BaseModel):
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    context_version: str = "v1"
    builder_version: str = "v1"
    provider_versions: dict[str, str] = Field(default_factory=dict)
    privacy_level: PrivacyLevel
    context_profile: ContextProfile = ContextProfile.SUMMARY
    token_estimate: int = 0
    article_id: int
    user_id: int | None = None
    anonymous_id: str | None = None
    cache_hit: bool = False
    generation_latency: float = 0.0

class ContextArticle(BaseModel):
    id: int
    title: str
    slug: str
    content: str  # The full text or chunk
    summary: str | None = None
    published_at: str | None = None
    source_name: str | None = None
    category: str | None = None
    entities: list[str] = Field(default_factory=list)

class ContextRelatedArticle(BaseModel):
    id: int
    title: str
    summary: str | None = None
    published_at: str | None = None
    url: str
    similarity_score: float

class ContextKnowledgeGraph(BaseModel):
    # Compressed representation of relevant nodes and relationships
    nodes: list[dict[str, str]] = Field(default_factory=list)
    relationships: list[dict[str, str]] = Field(default_factory=list)

class ContextBehavior(BaseModel):
    top_interests: list[str] = Field(default_factory=list)
    recent_categories: list[str] = Field(default_factory=list)
    reading_velocity_score: float = 0.0
    expertise_level: float = 0.0

class ContextCitation(BaseModel):
    id: str
    url: str
    title: str | None = None

class AIContext(BaseModel):
    metadata: AIContextMetadata
    primary_article: ContextArticle
    related_articles: list[ContextRelatedArticle] = Field(default_factory=list)
    knowledge_graph: ContextKnowledgeGraph = Field(default_factory=ContextKnowledgeGraph)
    behavior: ContextBehavior | None = None
    citations: list[ContextCitation] = Field(default_factory=list)

    def to_prompt_string(self) -> str:
        """Helper to dump the context efficiently for an LLM prompt."""
        return self.model_dump_json(exclude_none=True)

class ResearchContext(AIContext):
    question: str
    intent: str
    execution_plan: dict
    evidence_tree: dict
    confidence: dict
    snapshot_id: int
    reasoning_metadata: dict = Field(default_factory=dict)

class ConversationContext(AIContext):
    conversation_id: str
    episode_id: int
    working_memory: dict
    semantic_memory_refs: list[str]
    preference_memory_refs: list[str]
    research_session_id: int | None
    snapshot_id: int
    planner_history: list[str]
    artifact_history: list[int]
    execution_budget: dict

class ConversationResponse(BaseModel):
    message: str
    citations: list[ContextCitation] = Field(default_factory=list)
    artifacts: list[int] = Field(default_factory=list) # IDs of created/referenced artifacts
    workflow_summary: dict = Field(default_factory=dict)
    confidence: dict = Field(default_factory=dict)
    follow_up_questions: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    memory_updates: dict = Field(default_factory=dict)
    planner_trace: list[str] = Field(default_factory=list)
    execution_id: int | None = None
    artifact_lineage: dict = Field(default_factory=dict)
