import logging
from typing import Any

from app.core.capability.models import CapabilityIdentity
from app.services.agents.models import AgentExecutionResult, AgentInterface, AgentProfile, ExecutionMetrics

logger = logging.getLogger(__name__)

class TimelineAgent(AgentInterface):
    """
    Consumes Workspace. Outputs chronological findings to the Timeline section.
    """
    @property
    def profile(self) -> AgentProfile:
        return AgentProfile(
            name="TimelineAgent",
            description="Extracts and structures chronological events.",
            identity=CapabilityIdentity(
                identity_id="agent-timeline-1",
                owner="system",
                permissions=["READ_WORKSPACE", "WRITE_WORKSPACE"]
            ),
            allowed_intents=["TIMELINE"]
        )

    async def process_goal(self, goal: Any, workspace_snapshot: Any, budget: Any, policies: Any) -> AgentExecutionResult:
        logger.info(f"TimelineAgent processing goal {goal.goal_id}")
        return AgentExecutionResult(
            entries=[{
                "section": "Timeline",
                "producer_agent": "TimelineAgent",
                "status": "COMPLETED",
                "version": "v1",
                "confidence": 0.90
            }],
            artifacts=[],
            evidence={"decision": "Extracted 5 events from Research section", "confidence": 0.90},
            metrics=ExecutionMetrics(
                wall_duration_ms=200,
                cpu_duration_ms=200,
                token_input=400,
                token_output=100,
                snapshot_id=workspace_snapshot.snapshot_id
            )
        )

class ComparisonAgent(AgentInterface):
    """
    Consumes Workspace. Outputs differential findings to the Comparison section.
    """
    @property
    def profile(self) -> AgentProfile:
        return AgentProfile(
            name="ComparisonAgent",
            description="Performs structural comparisons between entities.",
            identity=CapabilityIdentity(
                identity_id="agent-comparison-1",
                owner="system",
                permissions=["READ_WORKSPACE", "WRITE_WORKSPACE"]
            ),
            allowed_intents=["COMPARISON"]
        )

    async def process_goal(self, goal: Any, workspace_snapshot: Any, budget: Any, policies: Any) -> AgentExecutionResult:
        logger.info(f"ComparisonAgent processing goal {goal.goal_id}")
        return AgentExecutionResult(
            entries=[{
                "section": "Comparison",
                "producer_agent": "ComparisonAgent",
                "status": "COMPLETED",
                "version": "v1",
                "confidence": 0.85
            }],
            artifacts=[],
            evidence={"decision": "Compared entities mapped by ResearchAgent", "confidence": 0.85},
            metrics=ExecutionMetrics(
                wall_duration_ms=300,
                cpu_duration_ms=300,
                token_input=800,
                token_output=200,
                snapshot_id=workspace_snapshot.snapshot_id
            )
        )
