import asyncio
from app.core.database import AsyncSessionLocal
from app.models.telemetry import TimelineNode, TimelineNodeType, RecoveryExecutionLog
from datetime import datetime, timezone
import time

async def inject_failure(correlation_id: str):
    """
    Scenario 05: Dispatcher Pause / Queue Saturation
    Simulates extreme queue depth indicating a stalled dispatcher or saturated worker pool.
    """
    print(f"[{correlation_id}] Simulating Queue Saturation telemetry...")
    
    async with AsyncSessionLocal() as db:
        from app.core.logging import correlation_id_ctx
        correlation_id_ctx.set(correlation_id)
        
        # 1. Detection
        node1 = TimelineNode(
            correlation_id=correlation_id,
            node_type=TimelineNodeType.HEALTH_CHECK,
            title="Queue Health Evaluation",
            description="Queue depth extremely high (5000+). Workers saturated."
        )
        db.add(node1)
        await db.commit()
        await db.refresh(node1)
        
        await asyncio.sleep(0.5)
        
        # 2. Recovery Triggered
        node2 = TimelineNode(
            correlation_id=correlation_id,
            node_type=TimelineNodeType.RECOVERY,
            title="QUEUE Recovery Triggered",
            description="Evaluating queue flush or worker pool scaling",
            caused_by_id=node1.id
        )
        db.add(node2)
        
        ledger = RecoveryExecutionLog(
            recovery_id=correlation_id,
            policy_name="QueueRecoveryPolicy",
            trigger_reason="Queue Saturation",
            mode="active",
            correlation_id=correlation_id
        )
        db.add(ledger)
        await db.commit()
        await db.refresh(ledger)
        
        await asyncio.sleep(0.5)
        
        # 3. Recovery Failed / Manual Required
        ledger.completed_at = datetime.now(timezone.utc)
        ledger.duration_ms = 1000
        ledger.success = False
        ledger.error_message = "Queue automation is disabled. Recommendation: Restart consumers or replay stalled work."
        
        node3 = TimelineNode(
            correlation_id=correlation_id,
            node_type=TimelineNodeType.RECOVERY,
            title="QUEUE Recovery Failed",
            description="Queue automation is disabled. Recommendation: Restart consumers or replay stalled work.",
            caused_by_id=node2.id
        )
        db.add(node3)
        await db.commit()
        
        # 4. Fire decouple analysis orchestration
        import os
        from app.tasks.root_cause_tasks import analyze_timeline_task, analyze_timeline
        if os.environ.get("CHAOS_RUNNER") == "1":
            await analyze_timeline(correlation_id)
        else:
            analyze_timeline_task.delay(correlation_id)
            
    print(f"[{correlation_id}] Dispatcher Pause / Queue Saturation injected.")
