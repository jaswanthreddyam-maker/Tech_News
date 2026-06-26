from typing import Any

from pydantic import BaseModel, Field


class PromptSafety(BaseModel):
    max_tokens: int = 4000
    temperature: float = 0.7
    banned_topics: list[str] = Field(default_factory=list)
    require_citations: bool = False

class PromptEvaluator(BaseModel):
    metric: str
    target_score: float

class PromptAsset(BaseModel):
    name: str
    version: str
    template: str
    variables: list[str]
    safety: PromptSafety
    guardrails: list[str]
    examples: list[dict[str, str]] = Field(default_factory=list)
    evaluators: list[PromptEvaluator] = Field(default_factory=list)

class InferenceRequest(BaseModel):
    prompt_asset_name: str
    prompt_asset_version: str
    variables: dict[str, Any]
    context: Any
