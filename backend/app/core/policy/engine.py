import logging
from typing import Any

from app.core.policy.models import BasePolicy, PolicyDecision

logger = logging.getLogger(__name__)

class PolicyPipeline:
    def __init__(self):
        self._policies: list[BasePolicy] = []

    def add_policy(self, policy: BasePolicy):
        self._policies.append(policy)
        self._policies.sort(key=lambda p: p.priority, reverse=True)

    @property
    def policies(self) -> list[BasePolicy]:
        return self._policies

class PolicyEngine:
    """
    Iterates over a PolicyPipeline to enforce constraints before capability execution.
    ADR-0044: Policy Before Execution.
    """
    def __init__(self, pipeline: PolicyPipeline):
        self.pipeline = pipeline

    async def execute(self, required_policies: list[str], context: Any) -> PolicyDecision:
        logger.info(f"PolicyEngine: Evaluating {len(self.pipeline.policies)} policies.")

        # We check all policies, prioritizing them appropriately.
        for policy in self.pipeline.policies:
            # If the capability requires specific policies, we could filter here, 
            # but generally enterprise policies (budget, safety) apply to everything globally.
            decision = await policy.evaluate(context)
            if not decision.allowed:
                logger.warning(f"Policy {policy.name} violated: {decision.reason}")
                if policy.stop_on_failure:
                    return decision

        return PolicyDecision(allowed=True)

class OptimizationApprovalPolicy(BasePolicy):
    """
    Evaluates self-optimization proposals.
    Safe optimizations (e.g. slight cache tweaks) can be auto-approved.
    Risky optimizations (e.g. concurrency limits) are left in PENDING_APPROVAL.
    """
    @property
    def name(self) -> str:
        return "optimization_approval_policy"

    async def evaluate(self, context: Any) -> PolicyDecision:
        artifact = getattr(context, "artifact", None)
        if not artifact or artifact.metadata.get("type") != "system_configuration":
            return PolicyDecision(allowed=True)

        # Example heuristic: if max_agent_concurrency > 50, require manual approval
        proposed_concurrency = artifact.content.get("max_agent_concurrency", 10)
        if proposed_concurrency > 50:
            return PolicyDecision(
                allowed=False,
                reason="Proposed max_agent_concurrency > 50 requires manual approval.",
                violated_policy=self.name,
                metadata={"status_override": "PENDING_APPROVAL"}
            )

        # Safe optimizations get auto-approved
        return PolicyDecision(allowed=True)
