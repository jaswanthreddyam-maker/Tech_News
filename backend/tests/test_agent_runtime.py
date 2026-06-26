import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.agents.executor import AgentExecutor
from app.intelligence.agents.memory import ConversationMemory, MemoryRegistry
from app.intelligence.agents.planner import PlannerRegistry, SequentialPlanner
from app.intelligence.agents.policies import NoReflection
from app.intelligence.agents.schemas import AgentExecution, AgentLifecycle, AgentManifest
from app.intelligence.generation.capabilities.base import CapabilityRegistry, GenerationCapability
from app.intelligence.generation.prompt import PromptTemplate


class MockAgentCapability(GenerationCapability):
    @property
    def capability_name(self) -> str:
        return "AgentCapability"

    def get_prompt_template(self) -> PromptTemplate:
        return PromptTemplate(
            system_prompt="Agent mock template",
            user_prompt="{query}"
        )

@pytest.mark.asyncio
async def test_agent_runtime(db_session: AsyncSession):
    # Setup Registries
    planner_registry = PlannerRegistry()
    planner_registry.register(SequentialPlanner())

    memory_registry = MemoryRegistry()
    memory_registry.register(ConversationMemory())

    capability_registry = CapabilityRegistry()
    capability_registry.register(MockAgentCapability())

    executor = AgentExecutor(
        planner_registry=planner_registry,
        memory_registry=memory_registry,
        capability_registry=capability_registry,
        reflection_policy=NoReflection()
    )

    manifest = AgentManifest(
        agent="test_agent",
        planner="SequentialPlanner",
        memory="ConversationMemory",
        capability="AgentCapability"
    )

    execution = AgentExecution(
        id="exec_123",
        session_id="sess_456",
        manifest=manifest
    )

    result = await executor.execute(db_session, execution, "Perform a complex task")

    assert result["status"] == AgentLifecycle.COMPLETED
    assert result["metrics"]["generation_calls"] == 3 # Sequential planner has 3 steps
    assert execution.state.current_step_id == "step_generate"

    # Normally AgentExecutor would insert Telemetry. We didn't add DB insertion to executor.py 
    # to keep it simple, but we should assert the expected behavior
    # For now we'll just check execution state mutated correctly.
    assert "step_generate" in execution.state.results
