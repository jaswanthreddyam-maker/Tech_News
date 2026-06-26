import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.telemetry import RootCauseAnalysis, RootCauseExplanation

async def run():
    async with AsyncSessionLocal() as db:
        analyses = await db.execute(select(RootCauseAnalysis.correlation_id, RootCauseAnalysis.root_cause, RootCauseAnalysis.confidence_score).where(RootCauseAnalysis.correlation_id.like("CHAOS-20260622-A473%")))
        print("Analysis for A473:", analyses.all())
        
        explanations = await db.execute(select(RootCauseExplanation.summary).join(RootCauseAnalysis).where(RootCauseAnalysis.correlation_id.like("CHAOS-20260622-A473%")))
        print("Explanation for A473:", explanations.all())

asyncio.run(run())
