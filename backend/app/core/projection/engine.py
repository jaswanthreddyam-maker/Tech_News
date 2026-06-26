import logging
import traceback

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.projection.context import ProjectionContext
from app.core.projection.executor import ProjectionExecutor
from app.core.projection.models import ProjectionCheckpoint, ProjectionFailure
from app.core.projection.registry import projector_registry
from app.core.projection.source import ProjectionSource
from app.models.event import EventEnvelope

logger = logging.getLogger(__name__)

class ProjectionEngine:
    """
    Universal Projection Engine.
    Consumes events, verifies checkpoints, invokes pure projectors, and applies mutations via executor.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.context = ProjectionContext(session)
        self.executor = ProjectionExecutor(session)

    async def process_stream(self, source: ProjectionSource, dry_run: bool = False):
        async for event in source.stream():
            await self.process_event(event, dry_run=dry_run)

    async def process_event(self, event: EventEnvelope, dry_run: bool = False):
        projectors = projector_registry.get_projectors_for_event(event.event_type)

        for projector in projectors:
            await self._process_projection(event, projector, dry_run=dry_run)

    async def _process_projection(self, event: EventEnvelope, projector, dry_run: bool):
        # 1. Check idempotency (only if not dry run)
        if not dry_run:
            chkpt_stmt = select(ProjectionCheckpoint).where(
                ProjectionCheckpoint.projection_group == projector.projection_group,
                ProjectionCheckpoint.projector_name == projector.name,
                ProjectionCheckpoint.event_id == event.id
            )
            existing = (await self.session.execute(chkpt_stmt)).scalar_one_or_none()
            if existing:
                return # Already processed

        # 2. Invoke Projector within a transactional savepoint
        async with self.session.begin_nested():
            try:
                # Projector is pure, returning a batch
                batch = await projector.project(event, self.context)

                if not dry_run:
                    # Execute mutations
                    await self.executor.execute_batch(batch)

                    # Record Checkpoint
                    checkpoint = ProjectionCheckpoint(
                        projection_group=projector.projection_group,
                        projector_name=projector.name,
                        projector_version=batch.version,
                        event_id=event.id
                    )
                    self.session.add(checkpoint)

                    # Clean up old failures if any
                    del_fail_stmt = delete(ProjectionFailure).where(
                        ProjectionFailure.projection_group == projector.projection_group,
                        ProjectionFailure.projector_name == projector.name,
                        ProjectionFailure.event_id == event.id
                    )
                    await self.session.execute(del_fail_stmt)

            except Exception as exc:
                if dry_run:
                    logger.error(f"[DRY RUN] Failed to project {event.id} with {projector.name}: {exc}")
                    return

                logger.error(f"Failed to project event {event.id} with {projector.name}: {exc}")
                err_msg = str(exc)
                err_tb = traceback.format_exc()

        # 3. Log failure outside the rolled-back savepoint if an exception occurred
        if 'err_msg' in locals() and not dry_run:
            async with self.session.begin_nested():
                fail_stmt = select(ProjectionFailure).where(
                    ProjectionFailure.projection_group == projector.projection_group,
                    ProjectionFailure.projector_name == projector.name,
                    ProjectionFailure.event_id == event.id
                )
                failure = (await self.session.execute(fail_stmt)).scalar_one_or_none()
                if not failure:
                    failure = ProjectionFailure(
                        projection_group=projector.projection_group,
                        projector_name=projector.name,
                        event_id=event.id,
                        error=err_msg,
                        stacktrace=err_tb,
                        attempt_count=1
                    )
                    self.session.add(failure)
                else:
                    failure.error = err_msg
                    failure.stacktrace = err_tb
                    failure.attempt_count += 1
                    failure.resolved = 0
            del err_msg
            del err_tb

class ReplayEngine:
    def __init__(self, session: AsyncSession, engine: ProjectionEngine):
        self.session = session
        self.engine = engine

    async def replay(self, source: ProjectionSource, projectors: list | None = None, dry_run: bool = False):
        """
        Replays events through the specified projectors.
        If projectors is None, reconfigures all matching.
        """
        if not dry_run and projectors:
            # Clear checkpoints for the projectors we are rebuilding
            for p in projectors:
                await self.session.execute(delete(ProjectionCheckpoint).where(
                    ProjectionCheckpoint.projection_group == p.projection_group,
                    ProjectionCheckpoint.projector_name == p.name
                ))
            await self.session.commit()

        await self.engine.process_stream(source, dry_run=dry_run)
