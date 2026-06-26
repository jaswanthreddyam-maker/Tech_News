from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.projection.context import ProjectionContext
from app.core.projection.mutations import InsertMutation, ProjectionBatch, SetMutation
from app.core.projection.projector import Projector
from app.models.event import EventEnvelope
from app.models.growth import Funnel, FunnelMetrics, FunnelState
from app.models.user import utc_now


class FunnelProjector(Projector):
    @property
    def projection_group(self) -> str:
        return "growth_funnels"

    @property
    def name(self) -> str:
        return "FunnelProjector"

    @property
    def version(self) -> int:
        return 1

    @property
    def supported_events(self) -> list[str]:
        return ["*"] # Subscribes to all events to check against active funnel matchers

    def _event_matches(self, event: EventEnvelope, matcher: dict[str, Any]) -> bool:
        if event.event_type != matcher.get("type"):
            return False

        conditions = matcher.get("conditions", {})
        if not conditions:
            return True

        payload = event.payload or {}
        # Simple AND matching for all key-value pairs in conditions
        return all(payload.get(k) == v for k, v in conditions.items())

    def _get_subject_for_funnel(self, event: EventEnvelope, subject_type: str) -> str:
        # Resolve subject identifier based on event and funnel subject_type
        if subject_type == "USER":
            return str(event.subject_id)
        elif subject_type == "SESSION":
            return str(event.session_id)
        # Fallback to subject_id
        return str(event.subject_id)

    async def project(self, event: EventEnvelope, context: ProjectionContext) -> ProjectionBatch:
        batch = ProjectionBatch(version=self.version)
        now = utc_now()

        # Load active funnels (in production this could be cached)
        stmt = select(Funnel).options(selectinload(Funnel.steps)).where(Funnel.status == "ACTIVE")
        funnels = await context.query(stmt)

        for funnel in funnels:
            if not funnel.steps:
                continue

            # Sort steps by order
            steps = sorted(funnel.steps, key=lambda x: x.step_order)
            total_steps = len(steps)

            # Find which step(s) match this event
            matched_step_index = -1
            for i, step in enumerate(steps):
                if self._event_matches(event, step.event_matcher):
                    matched_step_index = i
                    break

            if matched_step_index == -1:
                continue

            subject_id = self._get_subject_for_funnel(event, funnel.subject_type)
            if not subject_id:
                continue

            matched_step_order = steps[matched_step_index].step_order

            # Load metrics state for updating later
            metrics_bucket = datetime(now.year, now.month, now.day, tzinfo=now.tzinfo) # Daily bucket
            metrics = await context.load(FunnelMetrics, {"funnel_id": funnel.id, "time_bucket": metrics_bucket, "dimension_key": "ALL"})

            # We construct a dictionary that mimics the current metrics state to track changes
            if metrics:
                current_metrics: dict[str, Any] = {
                    "total_started": metrics.total_started,
                    "total_completed": metrics.total_completed,
                    "step_counts": dict(metrics.step_counts),
                    "id": metrics.id
                }
                metrics_exists = True
            else:
                current_metrics: dict[str, Any] = {
                    "total_started": 0,
                    "total_completed": 0,
                    "step_counts": {},
                    "id": None
                }
                metrics_exists = False

            state = await context.load(FunnelState, {"funnel_id": funnel.id, "subject_id": subject_id})

            state_updated = False

            if matched_step_order == 1:
                if not state:
                    # Enter funnel
                    expires_at = None
                    if funnel.time_window_seconds:
                        expires_at = now + timedelta(seconds=funnel.time_window_seconds)

                    batch.add(InsertMutation(
                        model=FunnelState,
                        values={
                            "funnel_id": funnel.id,
                            "subject_id": subject_id,
                            "dimension_snapshot": {}, # Sprint 4 placeholder
                            "current_step_order": 1,
                            "is_completed": total_steps == 1,
                            "started_at": now,
                            "entered_step_at": now,
                            "completed_at": now if total_steps == 1 else None,
                            "expires_at": expires_at
                        }
                    ))
                    state_updated = True
                    current_metrics["total_started"] += 1
                    current_metrics["step_counts"]["1"] = current_metrics["step_counts"].get("1", 0) + 1
                    if total_steps == 1:
                        current_metrics["total_completed"] += 1

            else:
                # Advancing in the funnel
                if state and not state.is_completed:
                    if state.expires_at and now > state.expires_at:
                        # Funnel expired
                        continue

                    # Strict sequential progression
                    if state.current_step_order == matched_step_order - 1:
                        is_completed = (matched_step_order == total_steps)
                        batch.add(SetMutation(model=FunnelState, target_id=state.id, field="current_step_order", value=matched_step_order))
                        batch.add(SetMutation(model=FunnelState, target_id=state.id, field="entered_step_at", value=now))

                        if is_completed:
                            batch.add(SetMutation(model=FunnelState, target_id=state.id, field="is_completed", value=True))
                            batch.add(SetMutation(model=FunnelState, target_id=state.id, field="completed_at", value=now))

                        state_updated = True
                        step_key = str(matched_step_order)
                        current_metrics["step_counts"][step_key] = current_metrics["step_counts"].get(step_key, 0) + 1
                        if is_completed:
                            current_metrics["total_completed"] += 1

            if state_updated:
                # Recalculate metrics
                started = current_metrics["total_started"]
                completed = current_metrics["total_completed"]
                conversion_rate = float(completed) / float(started) if started > 0 else 0.0
                dropoff_rate = 1.0 - conversion_rate if started > 0 else 0.0

                if metrics_exists:
                    batch.add(SetMutation(model=FunnelMetrics, target_id=current_metrics["id"], field="total_started", value=started))
                    batch.add(SetMutation(model=FunnelMetrics, target_id=current_metrics["id"], field="total_completed", value=completed))
                    batch.add(SetMutation(model=FunnelMetrics, target_id=current_metrics["id"], field="step_counts", value=current_metrics["step_counts"]))
                    batch.add(SetMutation(model=FunnelMetrics, target_id=current_metrics["id"], field="conversion_rate", value=conversion_rate))
                    batch.add(SetMutation(model=FunnelMetrics, target_id=current_metrics["id"], field="dropoff_rate", value=dropoff_rate))
                else:
                    batch.add(InsertMutation(
                        model=FunnelMetrics,
                        values={
                            "funnel_id": funnel.id,
                            "time_bucket": metrics_bucket,
                            "dimension_key": "ALL",
                            "total_started": started,
                            "total_completed": completed,
                            "step_counts": current_metrics["step_counts"],
                            "conversion_rate": conversion_rate,
                            "dropoff_rate": dropoff_rate
                        }
                    ))

        return batch

from app.core.projection.registry import projector_registry

projector_registry.register(FunnelProjector())
