import logging
from typing import Any

logger = logging.getLogger(__name__)

class PlatformScheduler:
    """
    Unified Runtime for all async execution (ADR-0062).
    Manages:
    - Priority queues
    - Delayed execution
    - Cron
    - Retries
    - Heartbeats
    - Leases
    - Concurrency limits
    - Backoff
    - Dead letters
    """
    def __init__(self, capability_bus, lease_manager, config_repository=None, event_bus=None):
        self.capability_bus = capability_bus
        self.lease_manager = lease_manager
        self.config_repository = config_repository
        self.event_bus = event_bus
        self._running = False

        # Default config fallback
        from app.core.config.models import SystemConfiguration
        self.current_config = SystemConfiguration(version_id="default")

    async def reload_configuration(self, version_id: str):
        """
        Hot-reloads the configuration from a PUBLISHED config artifact (ADR-0078).
        """
        if self.config_repository:
            config_artifact = await self.config_repository.get_published(version_id)
            if config_artifact:
                from app.core.config.models import SystemConfiguration
                self.current_config = SystemConfiguration(**config_artifact.content)
                logger.info(f"PlatformScheduler configuration hot-reloaded to version {version_id}")
            else:
                logger.warning(f"Failed to reload config: Version {version_id} not PUBLISHED.")
    async def start(self):
        self._running = True
        logger.info("PlatformScheduler (Runtime) started.")
        # Subscribe to domain events
        if self.event_bus:
            await self.event_bus.subscribe("ArtifactPublished", self.on_artifact_published)
        # Start heartbeat monitors, lease reapers, cron dispatchers, queue workers

    async def on_artifact_published(self, event: Any):
        """
        Event-driven hot reload (ADR-0038).
        Triggered when a system_configuration artifact transitions to PUBLISHED.
        """
        artifact_id = event.get("artifact_id")
        artifact_type = event.get("artifact_type")
        if artifact_type == "system_configuration":
            logger.info(f"PlatformScheduler received ArtifactPublished event for config {artifact_id}. Reloading.")
            await self.reload_configuration(artifact_id)

    async def stop(self):
        self._running = False
        logger.info("PlatformScheduler (Runtime) stopped.")

    async def apply_planner_result(self, goal_id: str, planner_result: Any):
        """
        Takes a PlannerResult, branches the workspace, and commits tasks.
        (ADR-0072)
        """
        logger.info(f"PlatformScheduler applying PlannerResult for goal {goal_id}")
        # Create branch in workspace
        # Append tasks to workspace branch
        pass

    async def submit_task(self, capability_name: str, version: str, payload: dict[str, Any], priority: int = 50):
        # Push to priority queue
        logger.info(f"Task submitted: {capability_name} (Priority {priority})")

    async def dispatch_workspace_tasks(self, workspace_snapshot: Any):
        """
        Inspects the Shared Workspace, resolves dependencies, leases tasks, and dispatches.
        (ADR-0068, ADR-0070)
        """
        ready_tasks = []
        for entry in workspace_snapshot.entries:
            if entry.status == "PENDING":
                # Check dependencies
                deps_met = True
                for dep in entry.dependencies:
                    dep_completed = any(
                        e.section == dep and e.status == "COMPLETED" 
                        for e in workspace_snapshot.entries
                    )
                    if not dep_completed:
                        deps_met = False
                        break

                if deps_met:
                    ready_tasks.append(entry)

        for task in ready_tasks:
            # 1. Acquire Lease
            lease_token = await self.lease_manager.acquire(
                resource_id=task.entry_id, 
                owner_id="scheduler-dispatcher",
                ttl_seconds=120
            )

            if lease_token:
                # 2. Dispatch to appropriate disposable agent via capability bus
                logger.info(f"PlatformScheduler leased Task {task.entry_id}. Dispatching to {task.section} agent.")
            else:
                logger.info(f"Task {task.entry_id} is already leased.")
