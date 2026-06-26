from app.ai.exceptions import AIProviderNotConfigured
from app.ai.providers.base import BaseAIProvider
from app.ai.schemas import AIProviderResponse, AITaskRequest


class AnthropicProvider(BaseAIProvider):
    provider_name = "anthropic"
    default_model = "claude-3-5-haiku"

    async def summarize(self, request: AITaskRequest) -> AIProviderResponse:
        raise AIProviderNotConfigured("Anthropic provider client is intentionally not implemented in Phase 4A.")

    async def generate_keywords(self, request: AITaskRequest) -> AIProviderResponse:
        raise AIProviderNotConfigured("Anthropic provider client is intentionally not implemented in Phase 4A.")

    async def generate_tags(self, request: AITaskRequest) -> AIProviderResponse:
        raise AIProviderNotConfigured("Anthropic provider client is intentionally not implemented in Phase 4A.")

    async def analyze_sentiment(self, request: AITaskRequest) -> AIProviderResponse:
        raise AIProviderNotConfigured("Anthropic provider client is intentionally not implemented in Phase 4A.")
