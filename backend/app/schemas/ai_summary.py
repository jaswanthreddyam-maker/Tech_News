from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.ai_artifacts import BaseAIArtifact


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
