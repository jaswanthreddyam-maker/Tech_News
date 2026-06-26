import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events.models import EventOutbox
from app.growth.rules import RuleRegistry
from app.growth.schemas import EvaluationTrace, FeatureFlagContext, FeatureFlagEvaluation
from app.models.growth import FeatureFlag, RuntimeConfiguration

logger = logging.getLogger(__name__)


class GrowthEvaluationEngine:
    """
    Engine for evaluating growth components (Feature Flags, Runtime Configs, Experiments) against a context.
    Provides deterministic evaluation and async telemetry emission with full execution traces.
    """

    @classmethod
    async def evaluate(
        cls, 
        item: FeatureFlag | RuntimeConfiguration, 
        context: FeatureFlagContext, 
        db_session: AsyncSession | None = None
    ) -> FeatureFlagEvaluation:
        """
        Evaluate an item (FeatureFlag or RuntimeConfiguration) against the given context.
        Optionally saves an event to the EventOutbox for telemetry.
        """
        trace_log: list[EvaluationTrace] = []
        env = context.environment
        env_states = item.environment_states or {}

        # 1. Check environment state
        if not env_states.get(env, False):
            result = FeatureFlagEvaluation(
                flag_key=item.key,
                value=item.default_value,
                reason=f"Environment '{env}' disabled",
                trace=trace_log,
                evaluation_version="v1"
            )
            await cls._emit_telemetry(result, context, db_session)
            return result

        # 2. Sort rules by priority (highest first)
        rules = item.rules or []
        sorted_rules = sorted(rules, key=lambda r: r.get("priority", 100), reverse=True)

        # 3. Evaluate rules sequentially (first match wins)
        for rule_def in sorted_rules:
            start_time = time.time()
            rule_type = rule_def.get("rule_type", "unknown")
            rule_config = rule_def.get("config", {})
            rule_version = rule_def.get("rule_version", "1.0")
            priority = rule_def.get("priority", 100)

            eval_value = RuleRegistry.evaluate(rule_type, context, rule_config, item.key, rule_version)

            execution_time_ms = (time.time() - start_time) * 1000.0
            matched = eval_value is not None

            trace_log.append(EvaluationTrace(
                environment=env,
                rule_name=rule_type,
                rule_version=rule_version,
                priority=priority,
                matched=matched,
                execution_time_ms=execution_time_ms
            ))

            if matched:
                result = FeatureFlagEvaluation(
                    flag_key=item.key,
                    value=eval_value,
                    reason="Rule match",
                    trace=trace_log,
                    evaluation_version="v1"
                )
                await cls._emit_telemetry(result, context, db_session)
                return result

        # 4. Fallback to default value
        result = FeatureFlagEvaluation(
            flag_key=item.key,
            value=item.default_value,
            reason="Default value fallback",
            trace=trace_log,
            evaluation_version="v1"
        )
        await cls._emit_telemetry(result, context, db_session)
        return result

    @classmethod
    async def _emit_telemetry(
        cls, 
        evaluation: FeatureFlagEvaluation, 
        context: FeatureFlagContext, 
        db_session: AsyncSession | None
    ):
        """
        Asynchronously queue the event to the Outbox if session is provided.
        """
        if not db_session:
            return

        try:
            payload = {
                "flag_key": evaluation.flag_key,
                "value": evaluation.value,
                "reason": evaluation.reason,
                "trace": [t.model_dump() for t in evaluation.trace],
                "evaluation_version": evaluation.evaluation_version,
                "context": context.model_dump()
            }

            # Use isoformat for datetime objects in context
            if payload["context"].get("timestamp"):
                payload["context"]["timestamp"] = payload["context"]["timestamp"].isoformat()

            outbox_event = EventOutbox(
                event_type="GROWTH_EVALUATED",
                payload=payload
            )
            db_session.add(outbox_event)
            # We do NOT commit here. The caller should commit their transaction.
        except Exception as e:
            logger.error(f"Failed to queue GROWTH_EVALUATED telemetry: {e}")
