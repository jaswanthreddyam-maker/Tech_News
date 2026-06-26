from pydantic import BaseModel


class RecommendationReason(BaseModel):
    type: str
    message: str

class RecommendationResponse(BaseModel):
    article: dict  # The article dict or schema
    score: float
    confidence: float
    reason: RecommendationReason
    strategy: str
