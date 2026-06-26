import logging
import time
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.chat import ChatProvider, StreamChunk
from app.intelligence.generation.context import AIContext
from app.intelligence.generation.interfaces import (
    InputValidator,
    MemoryProvider,
    Planner,
    RecoveryStrategy,
)
from app.intelligence.generation.prompt import PromptBuilder, PromptTemplate
from app.intelligence.generation.validation import OutputValidatorRegistry
from app.models.intelligence import GenerationTelemetry

logger = logging.getLogger(__name__)

class StreamAdapter:
    def __init__(self, generator: AsyncGenerator[StreamChunk, None]):
        self.generator = generator

    async def stream(self) -> AsyncGenerator[str, None]:
        async for chunk in self.generator:
            if chunk.chunk_text:
                yield chunk.chunk_text

class GenerationPipeline:
    """
    The unified Generation OS Primitive.
    Input -> Guardrails -> Planner -> Memory -> Retrieval -> Context -> Prompt -> Generation -> Tool Loop -> Validation -> Output.
    """
    def __init__(
        self,
        chat_provider: ChatProvider,
        prompt_template: PromptTemplate,
        input_validators: list[InputValidator] | None = None,
        planner: Planner | None = None,
        memory_providers: list[MemoryProvider] | None = None,
        retrievers: list[Any] | None = None,
        context_stages: list[Any] | None = None,
        tool_registry: Any | None = None, # ToolRegistry
        output_validators: OutputValidatorRegistry | None = None,
        recovery_strategy: RecoveryStrategy | None = None
    ):
        self.provider = chat_provider
        self.prompt_builder = PromptBuilder(prompt_template)

        self.input_validators = input_validators or []
        self.planner = planner
        self.memory_providers = memory_providers or []
        self.retrievers = retrievers or []
        self.context_stages = context_stages or []
        self.tool_registry = tool_registry
        self.output_validators = output_validators or OutputValidatorRegistry([])
        self.recovery_strategy = recovery_strategy

    async def execute(self, db: AsyncSession, context: AIContext, stream: bool = False, capability_name: str = "UnknownCapability") -> Any:
        start_time = time.time()

        tool_count = 0
        if self.tool_registry:
            tools = await self.tool_registry.get_all_tools()
            tool_count = len(tools)

        telemetry = GenerationTelemetry(
            capability_name=capability_name,
            query_text=context.query,
            provider_name=self.provider.provider_name,
            model_name=self.provider.default_model,
            tool_count=tool_count
        )

        # 1. Input Validation (Guardrails)
        for validator in self.input_validators:
            if not validator.validate(context):
                raise ValueError("Input validation failed")

        # 2. Planner (Stub)
        if self.planner:
            await self.planner.generate_plan(context)

        # 3. Memory Retrieval
        for memory in self.memory_providers:
            await memory.load_memory(context)

        # 4. Retrieval
        retrieval_start = time.time()
        if self.retrievers:
            all_chunks = []
            for r in self.retrievers:
                chunks = await r.retrieve(db, context.query, filters=context.filters)
                all_chunks.extend(chunks)
            context.retrieved_chunks = all_chunks
        telemetry.retrieval_latency_ms = int((time.time() - retrieval_start) * 1000)

        # 5. Context Processing
        for stage in self.context_stages:
            context = stage.execute(context)
        telemetry.context_chunk_count = len(context.compressed_chunks)

        # 6. Prompt Assembly
        prompt_start = time.time()
        messages = self.prompt_builder.build(context)
        telemetry.prompt_latency_ms = int((time.time() - prompt_start) * 1000)

        # 7. Generation / Tool Loop
        gen_start = time.time()
        if stream:
            # Tool loop not fully supported in simple streaming stub yet
            raw_stream = self.provider.generate_stream(messages)
            adapter = StreamAdapter(raw_stream)
            telemetry.total_latency_ms = int((time.time() - start_time) * 1000)

            db.add(telemetry)
            await db.commit()
            return adapter.stream()

        else:
            try:
                # Stub Tool Loop: Just one generation pass for now
                response_text = await self.provider.generate(messages)
            except Exception as e:
                if self.recovery_strategy:
                    response_text = await self.recovery_strategy.recover(e, context)
                else:
                    raise e

            telemetry.generation_latency_ms = int((time.time() - gen_start) * 1000)

            # 8. Output Validation
            val_start = time.time()
            val_result = self.output_validators.execute_all(response_text, context)
            telemetry.is_valid_citations = val_result["is_valid"]
            telemetry.validation_latency_ms = int((time.time() - val_start) * 1000)

            telemetry.total_latency_ms = int((time.time() - start_time) * 1000)
            db.add(telemetry)
            await db.commit()

            return {
                "answer": response_text,
                "citations": val_result.get("details", {}),
                "retrieved_documents": context.compressed_chunks,
                "provider": self.provider.provider_name,
                "model": self.provider.default_model,
                "telemetry": {
                    "total_latency_ms": telemetry.total_latency_ms,
                    "retrieval_latency_ms": telemetry.retrieval_latency_ms,
                    "generation_latency_ms": telemetry.generation_latency_ms,
                    "validation_latency_ms": telemetry.validation_latency_ms
                }
            }
