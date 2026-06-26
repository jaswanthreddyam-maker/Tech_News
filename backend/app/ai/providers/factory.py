from app.ai.exceptions import AIConfigurationError
from app.ai.providers.anthropic import AnthropicProvider
from app.ai.providers.base import BaseAIProvider, DisabledAIProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.openai import OpenAIProvider


def build_ai_provider(provider_name: str) -> BaseAIProvider:
    normalized = provider_name.strip().lower()
    providers: dict[str, type[BaseAIProvider]] = {
        "disabled": DisabledAIProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
    }
    provider_cls = providers.get(normalized)
    if provider_cls is None:
        known = ", ".join(sorted(providers))
        raise AIConfigurationError(f"Unknown AI provider '{provider_name}'. Expected one of: {known}.")

    if normalized == "openai":
        from app.core.config import settings

        return OpenAIProvider(api_key=settings.OPENAI_API_KEY)

    return provider_cls()
