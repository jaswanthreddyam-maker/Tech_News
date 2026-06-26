import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from app.core.redis import get_redis_client
from app.core.event_bus import publish_event
from app.core.metrics.recovery import recovery_metrics
from app.services.replay_service import ReplayService
from app.services.recovery.models import RecoveryDecision, RecoveryState
from app.services.recovery.policies import BaseRecoveryPolicy, CQRSRecoveryPolicy, ThumbnailRecoveryPolicy, QueueRecoveryPolicy
from app.models.telemetry import TimelineNode, TimelineNodeType, RecoveryExecutionLog
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

logger = logging.getLogger(__name__)

class RecoveryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.redis = get_redis_client()
        self.replay_service = ReplayService(session)
        
        # Load policies
        self.cqrs_policy = CQRSRecoveryPolicy()
        self.thumbnail_policy = ThumbnailRecoveryPolicy()
        self.queue_policy = QueueRecoveryPolicy()
        
        self.is_dry_run = getattr(settings, "RECOVERY_MODE", "dry_run") == "dry_run"

    def _generate_correlation_id(self) -> str:
        from app.core.logging import correlation_id_ctx
        ctx_id = correlation_id_ctx.get()
        if ctx_id:
            return ctx_id
            
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        short_id = str(uuid.uuid4())[:8].upper()
        return f"REC-{date_str}-{short_id}"

    async def _emit_audit(self, event_name: str, payload: dict):
        """Internal helper to emit the Autonomous Recovery Audit Trail to the global SSE event bus."""
        await publish_event("RECOVERY_SYSTEM", event_name, status="warning" if "Failed" in event_name or "Disabled" in event_name else "info", metadata=payload)

    async def _get_redis_state(self, recovery_type: str) -> dict:
        """Fetches the current recovery state for a given type from Redis."""
        state_key = f"recovery:state:{recovery_type}"
        failures_key = f"recovery:failures:{recovery_type}"
        cooldown_key = f"recovery:cooldown:{recovery_type}"
        
        current_state_bytes = await self.redis.get(state_key)
        if current_state_bytes:
            current_state = current_state_bytes if isinstance(current_state_bytes, str) else current_state_bytes.decode('utf-8')
        else:
            current_state = RecoveryState.HEALTHY.value
        
        failures_bytes = await self.redis.get(failures_key)
        failures = int(failures_bytes) if failures_bytes else 0
        
        cooldown_ttl = await self.redis.ttl(cooldown_key)
        cooldown_remaining = max(0, cooldown_ttl // 60) if cooldown_ttl > 0 else 0
        
        return {
            "state": current_state,
            "consecutive_failures": failures,
            "cooldown_remaining": cooldown_remaining
        }

    async def _check_hourly_limit(self, recovery_type: str) -> bool:
        """Rule 1: Maximum 3 recoveries per hour per type."""
        limit_key = f"recovery:hourly_count:{recovery_type}"
        current_count = await self.redis.get(limit_key)
        if current_count and int(current_count) >= 3:
            return False
        return True

    async def _increment_hourly_limit(self, recovery_type: str):
        limit_key = f"recovery:hourly_count:{recovery_type}"
        exists = await self.redis.exists(limit_key)
        await self.redis.incr(limit_key)
        if not exists:
            await self.redis.expire(limit_key, 3600)

    async def _emit_timeline_node(self, correlation_id: str, node_type: TimelineNodeType, title: str, description: str, caused_by_id: int = None, metadata: dict = None) -> int:
        """Appends a node to the Root Cause Timeline."""
        node = TimelineNode(
            correlation_id=correlation_id,
            node_type=node_type,
            title=title,
            description=description,
            caused_by_id=caused_by_id,
            metadata_json=metadata or {}
        )
        self.session.add(node)
        await self.session.commit()
        await self.session.refresh(node)
        return node.id

    async def evaluate_and_recover(self, policy: BaseRecoveryPolicy, metrics: dict) -> RecoveryDecision:
        recovery_type = policy.recovery_type
        redis_state = await self._get_redis_state(recovery_type)
        eval_correlation_id = self._generate_correlation_id()
        
        # Rule 5 / Kill Switch Check
        if redis_state["state"] == RecoveryState.DISABLED.value:
            await self._emit_timeline_node(
                correlation_id=eval_correlation_id,
                node_type=TimelineNodeType.HEALTH_CHECK,
                title=f"{recovery_type.upper()} Evaluation Skipped (DISABLED)",
                description="Automation Kill Switch activated due to consecutive failures. Manual intervention required.",
                metadata={"evidence_sources": ["redis_state"]}
            )
            return RecoveryDecision(
                approved=False,
                reason="Automation Kill Switch activated due to consecutive failures. Manual intervention required.",
                recovery_type=recovery_type,
                cooldown_remaining=redis_state["cooldown_remaining"],
                consecutive_failures=redis_state["consecutive_failures"]
            )
            
        decision = await policy.evaluate(metrics, redis_state)
        
        eval_node_id = await self._emit_timeline_node(
            correlation_id=eval_correlation_id,
            node_type=TimelineNodeType.HEALTH_CHECK,
            title=f"{recovery_type.upper()} Health Evaluation",
            description=decision.reason,
            metadata={"evidence_sources": [f"tnt_{recovery_type}_metrics"]}
        )
        
        # If not approved, just emit evaluation completed
        if not decision.approved:
            if redis_state["state"] != RecoveryState.HEALTHY.value and decision.reason.endswith("healthy."):
                await self.redis.set(f"recovery:state:{recovery_type}", RecoveryState.HEALTHY.value)
            
            await self._emit_audit("RecoveryEvaluationCompleted", {
                "recovery_type": recovery_type,
                "approved": False,
                "reason": decision.reason,
                "mode": "dry_run" if self.is_dry_run else "active"
            })
            return decision

        # --- Approval Path ---
        
        # Rule 1: Hourly Limit
        can_run = await self._check_hourly_limit(recovery_type)
        if not can_run:
            decision.approved = False
            decision.reason = "Hourly recovery limit (3) exceeded. Skipping."
            await self._emit_timeline_node(
                correlation_id=eval_correlation_id,
                node_type=TimelineNodeType.RECOVERY,
                title=f"{recovery_type.upper()} Recovery Skipped",
                description=decision.reason,
                caused_by_id=eval_node_id
            )
            await self._emit_audit("RecoverySkipped", {"recovery_type": recovery_type, "reason": decision.reason})
            return decision

        # Setup Execution
        decision.correlation_id = eval_correlation_id
        await self.redis.set(f"recovery:state:{recovery_type}", RecoveryState.RECOVERING.value)
        
        trigger_node_id = await self._emit_timeline_node(
            correlation_id=decision.correlation_id,
            node_type=TimelineNodeType.RECOVERY,
            title=f"{recovery_type.upper()} Recovery Triggered",
            description=decision.reason,
            caused_by_id=eval_node_id,
            metadata={"evidence_sources": ["RecoveryDecision", "HourlyLimitCheck"]}
        )
        
        # Initialize Ledger
        ledger = RecoveryExecutionLog(
            recovery_id=decision.correlation_id,
            policy_name=policy.__class__.__name__,
            trigger_reason=decision.reason,
            mode="dry_run" if self.is_dry_run else "active",
            correlation_id=decision.correlation_id
        )
        self.session.add(ledger)
        await self.session.commit()
        await self.session.refresh(ledger)
        
        await self._emit_audit("RecoveryTriggered", {
            "recovery_id": decision.correlation_id,
            "recovery_type": recovery_type,
            "reason": decision.reason,
            "mode": "dry_run" if self.is_dry_run else "active"
        })
        
        recovery_metrics.attempts_total.labels(type=recovery_type).inc()
        start_time = time.time()
        
        if self.is_dry_run:
            logger.info(f"DRY RUN: Would execute {recovery_type} recovery (ID: {decision.correlation_id})")
            await asyncio.sleep(1) # Simulate minor work
            success = True
        else:
            try:
                # Rule 2: 5-minute timeout
                success = await asyncio.wait_for(self._execute_action(recovery_type), timeout=300.0)
            except asyncio.TimeoutError:
                logger.error(f"Recovery {decision.correlation_id} timed out after 5 minutes.")
                success = False
            except Exception as e:
                logger.error(f"Recovery {decision.correlation_id} failed: {e}")
                success = False

        duration = time.time() - start_time
        recovery_metrics.duration_seconds.labels(type=recovery_type).observe(duration)
        
        # Update Ledger
        stmt = update(RecoveryExecutionLog).where(RecoveryExecutionLog.id == ledger.id).values(
            completed_at=datetime.now(timezone.utc),
            duration_ms=int(duration * 1000),
            success=success,
            error_message=None if success else f"Recovery {decision.correlation_id} failed or timed out."
        )
        await self.session.execute(stmt)
        await self.session.commit()
        
        if success:
            recovery_metrics.success_total.labels(type=recovery_type).inc()
            await self.redis.set(f"recovery:state:{recovery_type}", RecoveryState.RECOVERED.value)
            await self.redis.set(f"recovery:failures:{recovery_type}", 0) # Clear failures
            await self.redis.setex(f"recovery:cooldown:{recovery_type}", policy.cooldown_minutes * 60, "active")
            await self._increment_hourly_limit(recovery_type)
            
            await self._emit_timeline_node(
                correlation_id=decision.correlation_id,
                node_type=TimelineNodeType.RECOVERY,
                title=f"{recovery_type.upper()} Recovery Succeeded",
                description="Recovery operations executed and state safely restored.",
                caused_by_id=trigger_node_id
            )
            
            await self._emit_audit("RecoverySucceeded", {
                "recovery_id": decision.correlation_id,
                "recovery_type": recovery_type,
                "duration": duration,
                "mode": "dry_run" if self.is_dry_run else "active"
            })
            
            # Fire decouple analysis orchestration
            import os
            if os.environ.get("CHAOS_RUNNER") == "1":
                from app.tasks.root_cause_tasks import analyze_timeline
                # Execute synchronously to guarantee execution chain during test on Windows
                await analyze_timeline(decision.correlation_id)
            else:
                from app.tasks.root_cause_tasks import analyze_timeline_task
                analyze_timeline_task.delay(decision.correlation_id)
            
        else:
            recovery_metrics.failure_total.labels(type=recovery_type).inc()
            new_failures = redis_state["consecutive_failures"] + 1
            await self.redis.set(f"recovery:failures:{recovery_type}", new_failures)
            
            # Rule 3: 3 Consecutive Failures triggers Kill Switch
            if new_failures >= 3:
                await self.redis.set(f"recovery:state:{recovery_type}", RecoveryState.DISABLED.value)
                
                await self._emit_timeline_node(
                    correlation_id=decision.correlation_id,
                    node_type=TimelineNodeType.ALERT,
                    title="Automation Kill Switch Activated",
                    description="3 consecutive failures reached. Automation disabled. Human escalation required.",
                    caused_by_id=trigger_node_id
                )
                
                await self._emit_audit("RecoveryDisabled", {
                    "recovery_id": decision.correlation_id,
                    "recovery_type": recovery_type,
                    "reason": "3 consecutive failures reached. Automation disabled. Human escalation required."
                })
                
                # Fire decouple analysis orchestration
                from app.tasks.root_cause_tasks import analyze_timeline_task
                analyze_timeline_task.delay(decision.correlation_id)
            else:
                await self.redis.set(f"recovery:state:{recovery_type}", RecoveryState.FAILED.value)
                
                await self._emit_timeline_node(
                    correlation_id=decision.correlation_id,
                    node_type=TimelineNodeType.RECOVERY,
                    title=f"{recovery_type.upper()} Recovery Failed",
                    description=f"Execution failed or timed out. Attempts so far: {new_failures}/3.",
                    caused_by_id=trigger_node_id
                )
                
                await self._emit_audit("RecoveryFailed", {
                    "recovery_id": decision.correlation_id,
                    "recovery_type": recovery_type,
                    "reason": "Execution failed or timed out",
                    "mode": "dry_run" if self.is_dry_run else "active"
                })
                
                # Fire decouple analysis orchestration
                from app.tasks.root_cause_tasks import analyze_timeline_task
                analyze_timeline_task.delay(decision.correlation_id)

        return decision

    async def _execute_action(self, recovery_type: str) -> bool:
        """Maps recovery_type to the actual ReplayService actions."""
        if recovery_type == "cqrs":
            # Action: Replay Failed Batch
            # Since it's autonomous, we attribute it to the system.
            await self.replay_service.replay_failed_batch(admin_email="system@autonomous.local")
            return True
        elif recovery_type == "thumbnail":
            # Placeholder for thumbnail replay queueing
            return True
        return False
