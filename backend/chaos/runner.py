import asyncio
import json
import uuid
import time
from datetime import datetime, timezone
import os
import importlib.util
from app.core.database import AsyncSessionLocal
from app.models.telemetry import TimelineNode, TimelineNodeType, RecoveryExecutionLog, RootCauseAnalysis, RootCauseExplanation
from chaos.validator import validate_no_silent_failure
from app.core.logging import correlation_id_ctx

# SLAs in seconds
SLA_DETECTION = 30
SLA_RECOVERY = 60
SLA_ROOT_CAUSE = 120
SLA_EXPLANATION = 180

async def measure_slas(correlation_id: str, start_time: float):
    """
    Polls the DB to measure when each layer of the AIOps pipeline triggers.
    Returns the timings in seconds.
    """
    timings = {
        "detection_seconds": None,
        "recovery_seconds": None,
        "root_cause_seconds": None,
        "explanation_seconds": None
    }
    
    # We will poll for up to 200 seconds max
    max_wait = 200
    
    while time.time() - start_time < max_wait:
        elapsed = time.time() - start_time
        
        async with AsyncSessionLocal() as db:
            if timings["detection_seconds"] is None:
                from sqlalchemy import select
                stmt = select(TimelineNode.id).where(TimelineNode.correlation_id == correlation_id, TimelineNode.node_type == TimelineNodeType.HEALTH_CHECK)
                if (await db.execute(stmt)).first():
                    timings["detection_seconds"] = elapsed
                    
            if timings["recovery_seconds"] is None:
                from sqlalchemy import select
                stmt = select(RecoveryExecutionLog.id).where(RecoveryExecutionLog.correlation_id == correlation_id)
                if (await db.execute(stmt)).first():
                    timings["recovery_seconds"] = elapsed
                    
            if timings["root_cause_seconds"] is None:
                from sqlalchemy import select
                stmt = select(RootCauseAnalysis.id).where(RootCauseAnalysis.correlation_id == correlation_id)
                if (await db.execute(stmt)).first():
                    timings["root_cause_seconds"] = elapsed
                    
            if timings["explanation_seconds"] is None:
                from sqlalchemy import select
                stmt = select(RootCauseExplanation.id).join(RootCauseAnalysis).where(RootCauseAnalysis.correlation_id == correlation_id)
                if (await db.execute(stmt)).first():
                    timings["explanation_seconds"] = elapsed
                    
        if all(v is not None for v in timings.values()):
            break
            
        await asyncio.sleep(2)
        
    return timings

async def run_scenario(scenario_path: str, scenario_id: str):
    """
    Executes a single chaos scenario and measures its performance.
    """
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_uuid = str(uuid.uuid4())[:4].upper()
    correlation_id = f"CHAOS-{today}-{short_uuid}"
    
    print(f"Starting Chaos Execution: {correlation_id} (Scenario: {scenario_id})")
    
    # Enable test mode to bypass Celery for critical workflow steps (Windows stability)
    os.environ["CHAOS_RUNNER"] = "1"
    
    # Set the context so anything running in this thread picks it up
    correlation_id_ctx.set(correlation_id)
    start_time = time.time()
    
    # Dynamically load and run the scenario script
    spec = importlib.util.spec_from_file_location("chaos_scenario", scenario_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    if hasattr(module, 'inject_failure'):
        await module.inject_failure(correlation_id)
    else:
        print(f"Error: {scenario_path} missing inject_failure(correlation_id) async function.")
        return
        
    print(f"[{correlation_id}] Failure injected. Measuring SLAs...")
    
    timings = await measure_slas(correlation_id, start_time)
    
    print(f"[{correlation_id}] SLA Measurement Complete:")
    print(timings)
    
    # Enforce SLAs
    sla_passed = True
    if timings["detection_seconds"] is None or timings["detection_seconds"] > SLA_DETECTION: sla_passed = False
    if timings["recovery_seconds"] is None or timings["recovery_seconds"] > SLA_RECOVERY: sla_passed = False
    if timings["root_cause_seconds"] is None or timings["root_cause_seconds"] > SLA_ROOT_CAUSE: sla_passed = False
    if timings["explanation_seconds"] is None or timings["explanation_seconds"] > SLA_EXPLANATION: sla_passed = False
    
    # Validate No Silent Failures
    validation = await validate_no_silent_failure(correlation_id)
    silent_failure_passed = validation["passed"]
    
    success = sla_passed and silent_failure_passed
    
    result = {
        "scenario": scenario_id,
        "correlation_id": correlation_id,
        "detection_seconds": round(timings["detection_seconds"], 1) if timings["detection_seconds"] else None,
        "recovery_seconds": round(timings["recovery_seconds"], 1) if timings["recovery_seconds"] else None,
        "root_cause_seconds": round(timings["root_cause_seconds"], 1) if timings["root_cause_seconds"] else None,
        "explanation_seconds": round(timings["explanation_seconds"], 1) if timings["explanation_seconds"] else None,
        "sla_passed": sla_passed,
        "no_silent_failures": silent_failure_passed,
        "success": success,
        "validation_details": validation["details"]
    }
    
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(results_dir, exist_ok=True)
    
    result_path = os.path.join(results_dir, f"{correlation_id}.json")
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
        
    print(f"[{correlation_id}] Result saved to {result_path}. Success: {success}")
    return result

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python runner.py <path_to_scenario.py> <SCENARIO_ID>")
        sys.exit(1)
        
    asyncio.run(run_scenario(sys.argv[1], sys.argv[2]))
