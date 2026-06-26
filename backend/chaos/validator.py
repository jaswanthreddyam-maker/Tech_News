import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.telemetry import TimelineNode, TimelineNodeType, RecoveryExecutionLog, RootCauseAnalysis, RootCauseExplanation

async def validate_no_silent_failure(correlation_id: str) -> dict:
    """
    Enforces the 'No Silent Failure' certification rule.
    Given a chaos correlation ID, verifies that the complete observability and recovery chain fired.
    Returns a dict with pass/fail and details.
    """
    async with AsyncSessionLocal() as db:
        # 1. TimelineNode (Degraded Health Check)
        stmt = select(TimelineNode).where(TimelineNode.correlation_id == correlation_id, TimelineNode.node_type == TimelineNodeType.HEALTH_CHECK)
        health_nodes = (await db.execute(stmt)).scalars().all()
        has_health_check = len(health_nodes) > 0
        
        # 2. RecoveryExecutionLog
        stmt = select(RecoveryExecutionLog).where(RecoveryExecutionLog.correlation_id == correlation_id)
        recovery_log = (await db.execute(stmt)).scalars().first()
        has_recovery = recovery_log is not None
        
        # 3. RootCauseAnalysis
        stmt = select(RootCauseAnalysis).where(RootCauseAnalysis.correlation_id == correlation_id)
        analysis = (await db.execute(stmt)).scalars().first()
        has_analysis = analysis is not None
        
        # 4. RootCauseExplanation
        has_explanation = False
        if has_analysis:
            stmt = select(RootCauseExplanation).where(RootCauseExplanation.analysis_id == analysis.id)
            explanation = (await db.execute(stmt)).scalars().first()
            has_explanation = explanation is not None

        # Determine success
        passed = has_health_check and has_recovery and has_analysis and has_explanation
        
        return {
            "passed": passed,
            "details": {
                "health_check_detected": has_health_check,
                "recovery_triggered": has_recovery,
                "root_cause_generated": has_analysis,
                "explanation_generated": has_explanation
            }
        }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python validator.py <correlation_id>")
        sys.exit(1)
        
    cid = sys.argv[1]
    result = asyncio.run(validate_no_silent_failure(cid))
    print(f"Validation for {cid}: {'PASS' if result['passed'] else 'FAIL'}")
    print(result["details"])
