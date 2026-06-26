from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.intelligence.agents.memory import MemoryRegistry
from app.intelligence.agents.planner import PlannerRegistry
from app.intelligence.agents.policies import NoReflection, ReflectionPolicy
from app.intelligence.agents.schemas import AgentExecution, AgentLifecycle
from app.intelligence.generation.capabilities.base import CapabilityRegistry
from app.intelligence.generation.context import CapabilityContext
from app.models.intelligence import AgentTelemetry


class AgentContext(CapabilityContext):
    """
    Extends CapabilityContext for iterative agent execution.
    """
    execution_id: str
    session_id: str

class AgentExecutor:
    """
    High-level operational loop for Agent Executions.
    Routes Plan -> Graph -> Generation Pipeline -> Reflection -> Memory.
    """
    def __init__(
        self,
        planner_registry: PlannerRegistry,
        memory_registry: MemoryRegistry,
        capability_registry: CapabilityRegistry,
        reflection_policy: ReflectionPolicy = None
    ):
        self.planner_registry = planner_registry
        self.memory_registry = memory_registry
        self.capability_registry = capability_registry
        self.reflection_policy = reflection_policy or NoReflection()

    async def execute(self, db: AsyncSession, execution: AgentExecution, query: str) -> dict[str, Any]:
        execution.status = AgentLifecycle.PLANNING
        # We would emit AgentSessionStarted and PlanningStarted events here

        # 1. Planner Phase
        planner = self.planner_registry.get(execution.manifest.planner)
        graph = await planner.generate_plan(query, execution)

        execution.status = AgentLifecycle.EXECUTING
        # Emit ExecutingStarted event

        # 2. Memory Phase
        memory_provider = self.memory_registry.get(execution.manifest.memory)

        # 3. Step Execution Loop
        final_result = None
        for step in graph.steps:
            execution.state.current_step_id = step.id

            # Setup specific context for this iteration
            context = AgentContext(
                capability_name=execution.manifest.capability,
                execution_id=execution.id,
                session_id=execution.session_id,
                query=query # Would dynamically alter based on step
            )

            await memory_provider.load_memory(context)

            # Delegate tool loop and Generation to the frozen capability pipeline
            capability = self.capability_registry.get(execution.manifest.capability)

            # Note: The underlying pipeline will perform the Tool Loop (LLM -> Tool -> LLM) internally
            step_result = await capability.execute(db, context, stream=False)

            # Update state with pipeline telemetry
            execution.state.generation_calls += 1
            execution.state.tool_calls += step_result.get("telemetry", {}).get("tool_count", 0)

            # 4. Reflection Phase
            reflected_result = await self.reflection_policy.reflect(context, step_result)

            await memory_provider.save_memory(context, reflected_result)

            execution.state.results[step.id] = reflected_result
            final_result = reflected_result

            # Emit StepCompleted event

        execution.status = AgentLifecycle.COMPLETED
        # Emit ExecutionCompleted event

        telemetry = AgentTelemetry(
            execution_id=execution.id,
            session_id=execution.session_id,
            agent=execution.manifest.agent,
            planner=execution.manifest.planner,
            plan_version=graph.version,
            memory_provider=execution.manifest.memory,
            step_count=len(graph.steps),
            generation_calls=execution.state.generation_calls,
            tool_calls=execution.state.tool_calls,
            finish_reason="COMPLETED"
        )
        db.add(telemetry)
        await db.commit()

        return {
            "execution_id": execution.id,
            "status": execution.status,
            "final_result": final_result,
            "metrics": {
                "generation_calls": execution.state.generation_calls,
                "tool_calls": execution.state.tool_calls
            }
        }
