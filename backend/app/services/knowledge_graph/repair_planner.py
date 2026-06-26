import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import RepairPlan, RepairTask
from app.services.knowledge_graph.audit_suite import Finding

logger = logging.getLogger(__name__)

class RepairPlanner:
    """
    Converts Findings into immutable, event-sourced RepairPlans and RepairTasks.
    """
    def __init__(self):
        pass

    async def generate_plan(self, session: AsyncSession, findings: list[Finding]) -> list[RepairPlan]:
        plans = []
        for finding in findings:
            plan = RepairPlan(
                audit_type="GENERIC_AUDIT",
                description=f"Repair Plan for Finding: {finding.message}",
                status="PENDING"
            )
            session.add(plan)
            await session.flush()

            # Map recommended action to a specific task
            task = RepairTask(
                plan_id=plan.id,
                action_type=finding.recommended_action,
                target_id=finding.target_id,
                parameters={"severity": finding.severity},
                status="PENDING"
            )
            session.add(task)
            plans.append(plan)

        await session.flush()
        logger.info(f"RepairPlanner: Generated {len(plans)} immutable repair plans.")
        return plans
