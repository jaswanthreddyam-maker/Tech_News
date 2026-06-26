from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from app.ai.exceptions import AIProviderNotConfigured
from app.ai.schemas import AIProviderResponse, AITaskRequest


class ProviderCapabilities(BaseModel):
    supports_structured_outputs: bool = False
    supports_json_mode: bool = False
    supports_streaming: bool = False
    supports_tools: bool = False
    max_context: int = 4096

class BaseAIProvider(ABC):
    provider_name: str
    default_model: str
    response_format: str | None = None
    capabilities: ProviderCapabilities = ProviderCapabilities()

    @property
    def sdk_version(self) -> str | None:
        return None

    def provider_metadata_for(self, request: AITaskRequest) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "model": request.model,
            "prompt_version": request.prompt_version,
            "prompt_hash": request.prompt_hash,
            "sdk_version": self.sdk_version,
            "response_format": self.response_format,
        }

    @abstractmethod
    async def summarize(self, request: AITaskRequest) -> AIProviderResponse: ...

    @abstractmethod
    async def generate_keywords(self, request: AITaskRequest) -> AIProviderResponse: ...

    @abstractmethod
    async def generate_tags(self, request: AITaskRequest) -> AIProviderResponse: ...

    @abstractmethod
    async def analyze_sentiment(self, request: AITaskRequest) -> AIProviderResponse: ...


class DisabledAIProvider(BaseAIProvider):
    provider_name = "disabled"
    default_model = "phase4-foundation"

    async def summarize(self, request: AITaskRequest) -> AIProviderResponse:
        raise AIProviderNotConfigured("AI provider is disabled. Configure a concrete provider after Phase 4A.")

    async def generate_keywords(self, request: AITaskRequest) -> AIProviderResponse:
        raise AIProviderNotConfigured("AI provider is disabled. Configure a concrete provider after Phase 4A.")

    async def generate_tags(self, request: AITaskRequest) -> AIProviderResponse:
        raise AIProviderNotConfigured("AI provider is disabled. Configure a concrete provider after Phase 4A.")

    async def analyze_sentiment(self, request: AITaskRequest) -> AIProviderResponse:
        raise AIProviderNotConfigured("AI provider is disabled. Configure a concrete provider after Phase 4A.")
