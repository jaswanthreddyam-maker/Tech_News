import asyncio
from app.core.redis import get_redis_client

async def inject_failure(correlation_id: str):
    """
    Scenario 01: Disable RSS Source
    Simulates an upstream ingestion failure by marking a source as degraded.
    In the current framework, this triggers the Thumbnail Validation Failure
    to simulate external asset download failures and recovery.
    """
    client = get_redis_client()
    
    from app.services.recovery.service import RecoveryService
    from app.services.recovery.policies import ThumbnailRecoveryPolicy
    from app.core.database import AsyncSessionLocal
    
    print(f"[{correlation_id}] Simulating Thumbnail missing_rate metric spike...")
    
    await client.delete("recovery:cooldown:thumbnail")
    await client.delete("recovery:state:thumbnail")
    await client.delete("recovery:failures:thumbnail")
    await client.delete("recovery:hourly_count:thumbnail")
    
    async with AsyncSessionLocal() as db:
        service = RecoveryService(db)
        
        from app.core.logging import correlation_id_ctx
        correlation_id_ctx.set(correlation_id)
        
        metrics = {"missing_rate": 15.0} # Policy threshold is 10.0
        
        await service.evaluate_and_recover(ThumbnailRecoveryPolicy(), metrics)
        
    print(f"[{correlation_id}] Thumbnail validation failure injected into Recovery Engine.")
