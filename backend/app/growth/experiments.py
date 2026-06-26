import hashlib

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.events.models import EventOutbox
from app.growth.rules import RuleRegistry
from app.growth.schemas import FeatureFlagContext
from app.models.growth import Experiment, ExperimentAssignment, ExperimentVariant
from app.models.user import utc_now


class ExperimentEvaluationEngine:
    """
    Evaluates users for active experiments, handles sticky assignments, traffic allocation,
    and mutual exclusion. Emits EXPERIMENT_ASSIGNED and EXPERIMENT_EXPOSED telemetry.
    """

    @classmethod
    def _resolve_subject(cls, context: FeatureFlagContext, subject_type: str) -> str | None:
        mapping = {
            "USER": context.user_id,
            "SESSION": context.session_id,
            "DEVICE": context.device,
        }
        return mapping.get(subject_type)

    @classmethod
    async def evaluate(
        cls, 
        experiment: Experiment, 
        context: FeatureFlagContext, 
        db_session: AsyncSession
    ) -> ExperimentVariant | None:
        # 1. Environment & Status Check
        env = context.environment
        env_states = experiment.environment_states or {}
        if not env_states.get(env, False):
            return None

        if experiment.status != "RUNNING":
            return None

        # 2. Eligibility Check using Growth rules
        rules = experiment.rules or []
        sorted_rules = sorted(rules, key=lambda r: r.get("priority", 100), reverse=True)
        is_eligible = False

        if not rules:
            is_eligible = True
        else:
            for rule_def in sorted_rules:
                rule_type = rule_def.get("rule_type", "unknown")
                rule_config = dict(rule_def.get("config", {}))
                rule_version = rule_def.get("rule_version", "1.0")

                # We inject 'value': True just to check if the rule condition passes
                rule_config["value"] = True
                eval_value = RuleRegistry.evaluate(rule_type, context, rule_config, experiment.key, rule_version)
                if eval_value is True:
                    is_eligible = True
                    break

        if not is_eligible:
            return None

        # Resolve Subject
        subject_id = cls._resolve_subject(context, experiment.subject_type)
        if not subject_id:
            return None

        # 3. Existing Assignment Lookup
        query = select(ExperimentAssignment).where(
            ExperimentAssignment.experiment_id == experiment.id,
            ExperimentAssignment.subject_id == subject_id,
            ExperimentAssignment.subject_type == experiment.subject_type,
            ExperimentAssignment.is_active == True
        )
        result = await db_session.execute(query)
        assignment = result.scalar_one_or_none()

        if assignment:
            # Emit EXPERIMENT_EXPOSED only if window has passed
            EXPOSURE_WINDOW_SECONDS = 60
            now = utc_now()

            variant = next((v for v in experiment.variants if v.id == assignment.variant_id), None)

            # Idempotency check
            if (now - assignment.last_exposed_at).total_seconds() > EXPOSURE_WINDOW_SECONDS or assignment.exposure_count == 0:
                assignment.exposure_count += 1
                assignment.last_exposed_at = now
                await cls._emit_event("EXPERIMENT_EXPOSED", experiment, variant, assignment, context, db_session)

            return variant

        # 4. Mutual Exclusion Group
        if experiment.mutual_exclusion_group_id:
            mutex_query = select(ExperimentAssignment).join(Experiment, ExperimentAssignment.experiment_id == Experiment.id).where(
                Experiment.mutual_exclusion_group_id == experiment.mutual_exclusion_group_id,
                ExperimentAssignment.subject_id == subject_id,
                ExperimentAssignment.is_active == True,
                Experiment.id != experiment.id
            )
            mutex_result = await db_session.execute(mutex_query)
            if mutex_result.scalar_one_or_none():
                return None

        # 5. Traffic Allocation
        allocation_pct = experiment.allocation_percentage
        hash_input_alloc = f"{subject_id}_{experiment.key}_alloc".encode()
        bucket_alloc = int(hashlib.md5(hash_input_alloc).hexdigest()[:8], 16) % 100
        if bucket_alloc >= allocation_pct:
            return None

        # 6. Variant Selection (Normalized weighting)
        variants = experiment.variants
        if not variants:
            return None

        total_weight = sum(v.weight for v in variants)
        if total_weight == 0:
            return None

        hash_input_var = f"{subject_id}_{experiment.key}_variant".encode()
        hash_val = int(hashlib.md5(hash_input_var).hexdigest()[:8], 16)

        bucket_var = hash_val % total_weight

        assigned_variant = None
        current_sum = 0
        for v in variants:
            current_sum += v.weight
            if bucket_var < current_sum:
                assigned_variant = v
                break

        if not assigned_variant:
            return None

        # 7. Persistence
        new_assignment = ExperimentAssignment(
            experiment_id=experiment.id,
            variant_id=assigned_variant.id,
            subject_id=subject_id,
            subject_type=experiment.subject_type,
            assignment_hash=hashlib.md5(hash_input_var).hexdigest(),
            assignment_version=assigned_variant.version,
            exposure_count=1,
            assigned_at=utc_now(),
            last_exposed_at=utc_now(),
            is_active=True
        )
        db_session.add(new_assignment)

        # Flush to get the ID (if needed) or just rely on session state
        await db_session.flush()

        # 8. Telemetry
        await cls._emit_event("EXPERIMENT_ASSIGNED", experiment, assigned_variant, new_assignment, context, db_session)
        await cls._emit_event("EXPERIMENT_EXPOSED", experiment, assigned_variant, new_assignment, context, db_session)

        return assigned_variant

    @classmethod
    async def _emit_event(
        cls, 
        event_type: str, 
        experiment: Experiment, 
        variant: ExperimentVariant | None, 
        assignment: ExperimentAssignment, 
        context: FeatureFlagContext, 
        db_session: AsyncSession
    ):
        payload = {
            "experiment_key": experiment.key,
            "experiment_id": experiment.id,
            "variant_key": variant.key if variant else None,
            "variant_id": variant.id if variant else None,
            "subject_id": assignment.subject_id,
            "subject_type": assignment.subject_type,
            "assignment_hash": assignment.assignment_hash,
            "assignment_version": assignment.assignment_version,
            "exposure_count": assignment.exposure_count,
            "context": context.model_dump()
        }

        ctx = payload["context"]
        if isinstance(ctx, dict) and ctx.get("timestamp"):
            ctx["timestamp"] = ctx["timestamp"].isoformat()

        outbox_event = EventOutbox(
            event_type=event_type,
            payload=payload
        )
        db_session.add(outbox_event)
