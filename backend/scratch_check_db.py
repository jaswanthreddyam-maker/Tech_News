import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.telemetry import TimelineNode, RecoveryExecutionLog

async def run():
    async with AsyncSessionLocal() as db:
        logs = await db.execute(select(RecoveryExecutionLog.correlation_id, RecoveryExecutionLog.success, RecoveryExecutionLog.error_message).where(RecoveryExecutionLog.correlation_id.like("CHAOS-20260622-B6A9%")))
        print("Recovery Log for B6A9:", logs.all())
        
        nodes = await db.execute(select(TimelineNode.title).where(TimelineNode.correlation_id.like("CHAOS-20260622-B6A9%")))
        print("Nodes for B6A9:", nodes.all())

asyncio.run(run())
