import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.event_bus import publish_event
from app.core.projection.context import ProjectionContext
from app.core.projection.mutations import InsertMutation, ProjectionBatch, SetMutation
from app.core.projection.projector import Projector
from app.models.event import EventEnvelope
from app.models.growth import Cohort, CohortMembership
from app.models.user import utc_now

logger = logging.getLogger(__name__)

class CohortProjector(Projector):
    def __init__(self):
        # Optional: in-memory cache of cohorts index
        self._cohorts_cache = None

    @property
    def projection_group(self) -> str:
        return "growth_cohorts"

    @property
    def name(self) -> str:
        return "CohortProjector"

    @property
    def version(self) -> int:
        return 1

    @property
    def supported_events(self) -> list[str]:
        # We subscribe to all events to evaluate dynamic rules
        # In a real system, we'd index this based on active rules.
        return ["*"]

    def _evaluate_expression(self, expression: dict[str, Any], event: EventEnvelope) -> bool:
        """
        Evaluates a boolean expression.
        Format:
        {"operator": "AND", "operands": [...]}
        {"field": "event_type", "operator": "==", "value": "ARTICLE_VIEWED"}
        {"field": "payload.country", "operator": "==", "value": "US"}
        """
        if not expression:
            return True # Empty rule evaluates to True

        if "operator" not in expression:
            # Fallback to legacy simple equality if it's just key-values
            return all(not (k == "type" and event.event_type != v) for k, v in expression.items())

        op = expression["operator"]

        if op == "AND":
            return all(self._evaluate_expression(operand, event) for operand in expression.get("operands", []))
        elif op == "OR":
            return any(self._evaluate_expression(operand, event) for operand in expression.get("operands", []))
        elif op == "NOT":
            return not self._evaluate_expression(expression.get("operand", {}), event)

        # Leaf nodes
        field = expression.get("field")
        value = expression.get("value")

        if not field:
            return False

        # Resolve field value
        actual_value = None
        if field == "event_type":
            actual_value = event.event_type
        elif field.startswith("payload."):
            payload_key = field.split("payload.", 1)[1]
            actual_value = (event.payload or {}).get(payload_key)

        if op == "==":
            return bool(actual_value == value)
        elif op == "!=":
            return bool(actual_value != value)
        elif op == ">" and actual_value is not None:
            return float(actual_value) > float(value)
        elif op == "<" and actual_value is not None:
            return float(actual_value) < float(value)

        return False

    async def project(self, event: EventEnvelope, context: ProjectionContext) -> ProjectionBatch:
        batch = ProjectionBatch(version=self.version)
        now = utc_now()

        # Load active dynamic cohorts
        stmt = select(Cohort).options(selectinload(Cohort.rules)).where(
            Cohort.status == "ACTIVE",
            Cohort.refresh_mode == "REAL_TIME"
        )
        cohorts = await context.query(stmt)

        subject_id = event.subject_id
        if not subject_id:
            return batch

        for cohort in cohorts:
            if not cohort.rules:
                continue

            # For Sprint 5, we assume a user enters a cohort if any of its rules evaluate to True on this event.
            # In a more complex rule engine, a rule might count historical events, requiring us to check read-models.
            enters_cohort = False
            for rule in cohort.rules:
                if self._evaluate_expression(rule.expression, event):
                    enters_cohort = True
                    break

            if enters_cohort:
                # Check current membership
                membership = await context.load(CohortMembership, {"cohort_id": cohort.id, "subject_id": subject_id})

                if membership:
                    if membership.status != "ENTERED":
                        batch.add(SetMutation(model=CohortMembership, target_id=membership.id, field="status", value="ENTERED"))
                        batch.add(SetMutation(model=CohortMembership, target_id=membership.id, field="reason", value="Re-entered via dynamic rule"))
                        batch.add(SetMutation(model=CohortMembership, target_id=membership.id, field="added_at", value=now))
                        # Emitting side effect telemetry is usually done outside projection, but for Sprint 5 we mock it
                        await publish_event("COHORT_ENTERED", {"cohort_id": cohort.id, "subject_id": subject_id})
                else:
                    batch.add(InsertMutation(
                        model=CohortMembership,
                        values={
                            "cohort_id": cohort.id,
                            "subject_id": subject_id,
                            "status": "ENTERED",
                            "reason": "Dynamic rule matched",
                            "cohort_version": cohort.version,
                            "rule_version": "v1",
                            "projection_version": self.version,
                            "added_at": now
                        }
                    ))
                    await publish_event("COHORT_ENTERED", {"cohort_id": cohort.id, "subject_id": subject_id})
            else:
                # If they didn't match the enter condition, do they exit?
                # A proper rules engine defines enter AND exit criteria.
                # For this sprint, we assume if they don't match, they might exit if it's a strict property cohort.
                # We skip automatic exit unless explicitly defined to avoid thrashing.
                pass

        return batch

from app.core.projection.registry import projector_registry

projector_registry.register(CohortProjector())
