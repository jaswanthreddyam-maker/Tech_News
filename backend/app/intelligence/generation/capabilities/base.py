from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.chat import ChatProvider
from app.intelligence.generation.context import CapabilityContext
from app.intelligence.generation.interfaces import (
    InputValidator,
    MemoryProvider,
    OutputValidator,
    Planner,
    RecoveryStrategy,
    ToolProvider,
)
from app.intelligence.generation.pipeline import GenerationPipeline
from app.intelligence.generation.profiles import ProfileLoader
from app.intelligence.generation.prompt import PromptTemplate
from app.intelligence.generation.validation import OutputValidatorRegistry


class MockChatProvider(ChatProvider):
    @property
    def provider_name(self) -> str: return "mock"
    @property
    def default_model(self) -> str: return "mock-model"
    async def generate(self, messages, model=None, **kwargs):
        return "This is a mock generation response with citation [art_mock]."

class GenerationCapability:
    """
    Base class for declarative AI feature implementations.
    Every subclass defines its specific configuration, which is executed by the unified pipeline.
    """
    @property
    def capability_name(self) -> str:
        raise NotImplementedError

    @property
    def version(self) -> str:
        return "v1.0"

    def get_profile_name(self) -> str:
        return "Balanced"

    def get_prompt_template(self) -> PromptTemplate:
        raise NotImplementedError

    def get_retrievers(self) -> list[Any]:
        return []

    def get_input_validators(self) -> list[InputValidator]:
        return []

    def get_output_validators(self) -> list[OutputValidator]:
        return []

    def get_memory_providers(self) -> list[MemoryProvider]:
        return []

    def get_tool_providers(self) -> list[ToolProvider]:
        return []

    def get_planner(self) -> Planner | None:
        return None

    def get_recovery_strategy(self) -> RecoveryStrategy | None:
        return None

    async def execute(self, db: AsyncSession, context: CapabilityContext, stream: bool = False) -> Any:
        profile = await ProfileLoader.load(db, self.get_profile_name())

        # For sprint 3, we still use the MockChatProvider. In production, 
        # ChatProviderRegistry.get_provider(profile.provider) would be used.
        chat_provider = MockChatProvider()

        pipeline = GenerationPipeline(
            chat_provider=chat_provider,
            prompt_template=self.get_prompt_template(),
            input_validators=self.get_input_validators(),
            planner=self.get_planner(),
            memory_providers=self.get_memory_providers(),
            retrievers=self.get_retrievers(),
            context_stages=[], # We'll skip context deduplication in this bare capability runner for now
            output_validators=OutputValidatorRegistry(self.get_output_validators()),
            recovery_strategy=self.get_recovery_strategy()
        )

        return await pipeline.execute(db, context, stream, capability_name=self.capability_name)

class CapabilityRegistry:
    def __init__(self):
        self._capabilities: dict[str, GenerationCapability] = {}

    def register(self, capability: GenerationCapability):
        self._capabilities[capability.capability_name] = capability

    def get(self, name: str) -> GenerationCapability:
        if name not in self._capabilities:
            raise KeyError(f"Capability {name} not found in registry.")
        return self._capabilities[name]
