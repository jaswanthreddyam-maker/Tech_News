import hashlib
import logging
import uuid

from app.api.v2.models import IntentSchema, Operation, OperationStatus
from app.core.goal.models import Goal

logger = logging.getLogger(__name__)

class IntentApplicationService:
    """
    Translates an external Intent into an internal Goal, and returns an Operation.
    Controllers use this service instead of coupling to the Kernel.
    """
    def __init__(self, platform_scheduler, capability_registry=None):
        self.platform_scheduler = platform_scheduler
        self.capability_registry = capability_registry

    async def handle_intent(self, intent: IntentSchema, identity: str) -> Operation:
        logger.info(f"Translating Intent '{intent.action}' for user {identity} into Goal")

        # ADR-0080: Capability Exposure Policy
        if self.capability_registry and intent.target:
            contract = self.capability_registry.get_contract(intent.target)
            if contract and getattr(contract, "visibility", "internal") == "internal":
                # Or raise an HTTP exception, but we return a failed Operation for safety
                return Operation(
                    operation_id=f"op_{uuid.uuid4().hex[:12]}",
                    status=OperationStatus.FAILED,
                    message=f"Capability '{intent.target}' is internal and cannot be invoked externally."
                )

        operation_id = f"op_{uuid.uuid4().hex[:12]}"

        # Translate to Goal
        description = f"Action: {intent.action}. Target: {intent.target}."
        fingerprint = hashlib.sha256(f"{identity}:{description}".encode()).hexdigest()

        goal = Goal(
            goal_id=f"goal_{uuid.uuid4().hex[:8]}",
            owner_id=identity,
            description=description,
            fingerprint=fingerprint,
            metadata={"operation_id": operation_id, "source": "enterprise_api"}
        )

        # Submit to OS Execution Layer
        await self.platform_scheduler.submit_task(
            capability_name="COORDINATOR",
            version="v1",
            payload={"goal": goal.model_dump()},
            priority=50
        )

        # Return Public Operation
        return Operation(
            operation_id=operation_id,
            status=OperationStatus.QUEUED,
            message="Intent successfully mapped and enqueued."
        )
