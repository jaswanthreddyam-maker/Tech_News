from dataclasses import dataclass
from decimal import Decimal

from app.ai.schemas import TokenUsage


@dataclass(frozen=True)
class ModelPricing:
    prompt_per_million: Decimal
    completion_per_million: Decimal


MODEL_PRICING: dict[str, ModelPricing] = {
    "gpt-4o-mini": ModelPricing(Decimal("0.150"), Decimal("0.600")),
    "gpt-4.1-mini": ModelPricing(Decimal("0.400"), Decimal("1.600")),
    "claude-3-5-haiku": ModelPricing(Decimal("0.800"), Decimal("4.000")),
    "gemini-1.5-flash": ModelPricing(Decimal("0.075"), Decimal("0.300")),
    "phase4-foundation": ModelPricing(Decimal("0"), Decimal("0")),
}


def calculate_cost_usd(model: str, usage: TokenUsage) -> Decimal:
    pricing = MODEL_PRICING.get(model, ModelPricing(Decimal("0"), Decimal("0")))
    prompt_cost = Decimal(usage.prompt_tokens) * pricing.prompt_per_million / Decimal(1_000_000)
    completion_cost = Decimal(usage.completion_tokens) * pricing.completion_per_million / Decimal(1_000_000)
    return (prompt_cost + completion_cost).quantize(Decimal("0.000001"))
