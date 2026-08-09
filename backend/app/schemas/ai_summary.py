from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.ai_artifacts import BaseAIArtifact


class DocumentType(str, Enum):
    BREAKING_NEWS = "breaking_news"
    FEATURE = "feature"
    INTERVIEW = "interview"
    OPINION = "opinion"
    EDITORIAL = "editorial"
    REVIEW = "review"
    HOW_TO = "how_to"
    NEWSLETTER = "newsletter"
    ROUNDUP = "roundup"
    LIVE_BLOG = "live_blog"
    PRODUCT_ANNOUNCEMENT = "product_announcement"
    RESEARCH = "research"
    EXPLAINER = "explainer"


class SummaryTimelineEvent(BaseModel):
    date: str
    event: str
    confidence: float
    sources: list[str]

class SummaryEntity(BaseModel):
    name: str
    role: str | None = None
    importance: float
    sources: list[str]

class SummaryTakeaway(BaseModel):
    title: str
    description: str
    priority: int = Field(..., description="Priority of the takeaway (1, 2, or 3 where 1 is highest)")

class SummaryConfidenceMetrics(BaseModel):
    overall: float
    timeline: float
    entities: float
    takeaways: float

class StructuredSummaryMetadata(BaseModel):
    confidence: SummaryConfidenceMetrics
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    model_version: str
    context_version: str

class StructuredSummary(BaseAIArtifact):
    document_type: DocumentType = Field(
        default=DocumentType.BREAKING_NEWS,
        description="Document classification enum"
    )
    is_multi_topic: bool = Field(
        default=False,
        description="True if document contains multiple distinct topics or sections without a single >40% dominant topic."
    )
    primary_topics: list[str] = Field(
        default_factory=list,
        description="List of primary topics covered in the document"
    )
    dominant_topic_percentage: float = Field(
        default=100.0,
        description="Estimated percentage (0-100) of the document dedicated to the top primary topic."
    )
    headline: str
    executive_summary: str
    key_takeaways: list[SummaryTakeaway]
    timeline: list[SummaryTimelineEvent]
    people: list[SummaryEntity]
    organizations: list[SummaryEntity]
    technologies: list[SummaryEntity]
    risks: list[str]
    opportunities: list[str]
    open_questions: list[str]
    citations: list[str]
    summary_confidence: SummaryConfidenceMetrics
