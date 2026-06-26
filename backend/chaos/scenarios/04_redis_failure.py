import asyncio
from app.core.database import AsyncSessionLocal
from app.models.telemetry import TimelineNode, TimelineNodeType, RecoveryExecutionLog
from datetime import datetime, timezone
import time

async def inject_failure(correlation_id: str):
    """
    Scenario 04: Redis Connection Failure
    Simulates a Redis connection timeout.
    """
    print(f"[{correlation_id}] Simulating Redis Timeout telemetry...")
    
    async with AsyncSessionLocal() as db:
        from app.core.logging import correlation_id_ctx
        correlation_id_ctx.set(correlation_id)
        
        # 1. Detection
        node1 = TimelineNode(
            correlation_id=correlation_id,
            node_type=TimelineNodeType.HEALTH_CHECK,
            title="Infrastructure Health Evaluation",
            description="Redis connection timeout. Ping failed after 5000ms."
        )
        db.add(node1)
        await db.commit()
        await db.refresh(node1)
        
        await asyncio.sleep(0.5)
        
        # 2. Recovery Triggered
        node2 = TimelineNode(
            correlation_id=correlation_id,
            node_type=TimelineNodeType.RECOVERY,
            title="INFRASTRUCTURE Recovery Triggered",
            description="Restarting Redis service",
            caused_by_id=node1.id
        )
        db.add(node2)
        
        ledger = RecoveryExecutionLog(
            recovery_id=correlation_id,
            policy_name="InfrastructureRedisPolicy",
            trigger_reason="Redis timeout",
            mode="active",
            correlation_id=correlation_id
        )
        db.add(ledger)
        await db.commit()
        await db.refresh(ledger)
        
        await asyncio.sleep(0.5)
        
        # 3. Recovery Skipped / Failed (Manual Required)
        ledger.completed_at = datetime.now(timezone.utc)
        ledger.duration_ms = 1000
        ledger.success = False
        ledger.error_message = "Automated restart disabled for primary datastore. Manual intervention required."
        
        node3 = TimelineNode(
            correlation_id=correlation_id,
            node_type=TimelineNodeType.RECOVERY,
            title="INFRASTRUCTURE Recovery Failed",
            description="Automated restart disabled for primary datastore. Manual intervention required.",
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
            
    print(f"[{correlation_id}] Redis Failure injected.")
