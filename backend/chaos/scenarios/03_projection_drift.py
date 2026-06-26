import asyncio
from app.core.redis import get_redis_client
import time

async def inject_failure(correlation_id: str):
    """
    Scenario 03: Projection Drift Simulator
    Simulates projection drift by temporarily pausing the projection worker
    via a Redis feature flag that the worker respects, or simply by inserting
    a delay. In this environment, we'll explicitly trigger a projection_lag metric spike
    and emit the degraded health check node to kick off the Autonomous Recovery Engine,
    simulating the exact metrics a stalled worker would produce.
    """
    client = get_redis_client()
    
    # Simulate the metric spike that the health monitor would see
    from app.services.recovery.service import RecoveryService
    from app.services.recovery.policies import CQRSRecoveryPolicy
    from app.core.database import AsyncSessionLocal
    
    print(f"[{correlation_id}] Simulating CQRS Projection Lag metric spike...")
    
    # Reset any previous state or cooldowns to ensure determinism
    await client.delete("recovery:cooldown:cqrs")
    await client.delete("recovery:state:cqrs")
    await client.delete("recovery:failures:cqrs")
    await client.delete("recovery:hourly_count:cqrs")
    
    # We directly feed the degraded metric into the RecoveryService 
    # to simulate the monitoring beat detecting the drift.
    async with AsyncSessionLocal() as db:
        service = RecoveryService(db)
        
        # Override the correlation ID context so the service uses our CHAOS ID for the evaluation
        from app.core.logging import correlation_id_ctx
        correlation_id_ctx.set(correlation_id)
        
        # Inject metrics that violate the policy
        metrics = {"projection_lag": 15} # Policy threshold is 10
        
        # This will trigger:
        # 1. HEALTH_CHECK TimelineNode
        # 2. RECOVERY_TRIGGERED TimelineNode
        # 3. RecoveryExecutionLog
        # 4. Action (replay_failed_batch)
        # 5. RECOVERY_SUCCEEDED TimelineNode
        # 6. Celery task for AI Explanation
        await service.evaluate_and_recover(CQRSRecoveryPolicy(), metrics)
        
    print(f"[{correlation_id}] CQRS Projection Lag injected into Recovery Engine.")
