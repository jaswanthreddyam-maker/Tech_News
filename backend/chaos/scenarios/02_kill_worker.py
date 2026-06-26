import asyncio
from app.core.redis import get_redis_client
from app.core.database import AsyncSessionLocal
from app.models.telemetry import TimelineNode, TimelineNodeType, RecoveryExecutionLog
from datetime import datetime, timezone
import time

async def inject_failure(correlation_id: str):
    """
    Scenario 02: Celery Worker Termination
    Simulates a worker going offline and being detected/recovered.
    Since Worker Restart is an infrastructure-level operation typically 
    handled outside the application by k8s or systemd, we simulate the telemetry
    that would be emitted by the external orchestrator via our service layer.
    """
    print(f"[{correlation_id}] Simulating Worker Offline telemetry...")
    
    async with AsyncSessionLocal() as db:
        from app.core.logging import correlation_id_ctx
        correlation_id_ctx.set(correlation_id)
        
        # 1. Detection
        node1 = TimelineNode(
            correlation_id=correlation_id,
            node_type=TimelineNodeType.HEALTH_CHECK,
            title="Worker Health Evaluation",
            description="Celery worker beat is offline. No heartbeat detected in 60s."
        )
        db.add(node1)
        await db.commit()
        await db.refresh(node1)
        
        # Simulate delay
        await asyncio.sleep(0.5)
        
        # 2. Recovery Triggered
        node2 = TimelineNode(
            correlation_id=correlation_id,
            node_type=TimelineNodeType.RECOVERY,
            title="WORKER Recovery Triggered",
            description="Initiating systemctl restart celery-worker",
            caused_by_id=node1.id
        )
        db.add(node2)
        
        ledger = RecoveryExecutionLog(
            recovery_id=correlation_id,
            policy_name="InfrastructureWorkerPolicy",
            trigger_reason="Worker offline",
            mode="active",
            correlation_id=correlation_id
        )
        db.add(ledger)
        await db.commit()
        await db.refresh(ledger)
        
        # Simulate delay
        await asyncio.sleep(0.5)
        
        # 3. Recovery Succeeded
        ledger.completed_at = datetime.now(timezone.utc)
        ledger.duration_ms = 1200
        ledger.success = True
        
        node3 = TimelineNode(
            correlation_id=correlation_id,
            node_type=TimelineNodeType.RECOVERY,
            title="WORKER Recovery Succeeded",
            description="Worker restarted and heartbeat received.",
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
            
    print(f"[{correlation_id}] Worker Termination failure injected.")
