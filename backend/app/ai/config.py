from dataclasses import dataclass, field
from decimal import Decimal

from app.ai.schemas import AITaskType
from app.core.config import settings

DEFAULT_PROMPT_VERSIONS: dict[AITaskType, str] = {
    AITaskType.SUMMARY: "summary_v1",
    AITaskType.KEYWORDS: "seo_v1",
    AITaskType.TAGS: "tags_v1",
    AITaskType.SENTIMENT: "sentiment_v1",
    AITaskType.ENTITIES: "entities_v1",
    AITaskType.TOPICS: "topics_v1",
}


@dataclass(frozen=True)
class AIConfig:
    provider: str = field(default_factory=lambda: str(getattr(settings, "AI_PROVIDER", "disabled")).lower())
    providers: list[str] = field(
        default_factory=lambda: [
            p.strip()
            for p in str(getattr(settings, "AI_PROVIDER_PRIORITY", "openai,anthropic,gemini")).lower().split(",")
        ]
    )
    summary_model: str = field(default_factory=lambda: str(getattr(settings, "SUMMARY_MODEL", "gpt-4o-mini")))
    chat_model: str = field(default_factory=lambda: str(getattr(settings, "CHAT_MODEL", "gpt-4o-mini")))
    reasoning_model: str = field(default_factory=lambda: str(getattr(settings, "REASONING_MODEL", "gpt-4o")))
    embedding_model: str = field(
        default_factory=lambda: str(getattr(settings, "EMBEDDING_MODEL", "text-embedding-3-small"))
    )
    max_retries: int = field(default_factory=lambda: int(getattr(settings, "MAX_AI_RETRIES", 3)))
    request_timeout_seconds: float = field(
        default_factory=lambda: float(getattr(settings, "AI_REQUEST_TIMEOUT_SECONDS", 20.0))
    )
    max_input_chars: int = field(default_factory=lambda: int(getattr(settings, "AI_MAX_INPUT_CHARS", 12000)))
    max_output_tokens: int = field(default_factory=lambda: int(getattr(settings, "AI_MAX_OUTPUT_TOKENS", 700)))
    daily_budget_usd: Decimal = field(
        default_factory=lambda: Decimal(str(getattr(settings, "AI_DAILY_BUDGET_USD", "5.00")))
    )
    monthly_budget_usd: Decimal = field(
        default_factory=lambda: Decimal(str(getattr(settings, "AI_MONTHLY_BUDGET_USD", "75.00")))
    )
    prompt_versions: dict[AITaskType, str] = field(default_factory=lambda: DEFAULT_PROMPT_VERSIONS.copy())

    def prompt_version_for(self, task_type: AITaskType) -> str:
        return self.prompt_versions.get(task_type, f"{task_type.value}_v1")
