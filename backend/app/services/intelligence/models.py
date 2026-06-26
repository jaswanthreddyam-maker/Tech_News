from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class BaseIntelligenceNode(BaseModel):
    id: str
    confidence: float
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_artifacts: list[str] = Field(default_factory=list) # IDs of ReflectionArtifacts or other nodes

class Observation(BaseIntelligenceNode):
    """
    Raw structured fact extracted from reflection.
    e.g. "Node duplication increasing"
    """
    metric: str
    value: Any

class Finding(BaseIntelligenceNode):
    """
    Contextualized observation.
    e.g. "Node duplication increasing specifically in Technology entities"
    """
    description: str
    observations: list[str] # IDs of Observations

class Insight(BaseIntelligenceNode):
    """
    Synthesized meaning.
    e.g. "Entity resolution quality degrading"
    """
    description: str
    findings: list[str] # IDs of Findings

class Trend(BaseIntelligenceNode):
    """
    Temporal or recurring insight.
    e.g. "Entity resolution degrades by 5% every weekend"
    """
    description: str
    insights: list[str] # IDs of Insights
    velocity: float

class Prediction(BaseIntelligenceNode):
    """
    Forward-looking expectation.
    e.g. "We will hit 10% duplicate nodes next week"
    """
    description: str
    target_date: datetime | None = None
    trends: list[str] # IDs of Trends

class Recommendation(BaseIntelligenceNode):
    """
    Actionable system-level recommendation based on prediction.
    e.g. "Trigger a bulk deduplication workflow"
    """
    action: str
    parameters: dict[str, Any]
    predictions: list[str] # IDs of Predictions
