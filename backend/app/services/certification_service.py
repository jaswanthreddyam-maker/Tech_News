import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.certification import CertificationRun, CertificationScenarioEvidence

logger = logging.getLogger(__name__)

class CertificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_latest_successful_run(self, certification_type: str) -> Optional[CertificationRun]:
        stmt = (
            select(CertificationRun)
            .where(CertificationRun.certification_type == certification_type)
            .where(CertificationRun.passed == CertificationRun.total_scenarios)
            .where(CertificationRun.total_scenarios > 0)
            .order_by(CertificationRun.completed_at.desc())
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    def calculate_grade(self, passed: int, total: int, sla_failures: int) -> str:
        if total == 0:
            return "F"
            
        pass_rate = passed / total
        
        if pass_rate == 1.0:
            if sla_failures == 0:
                return "A+"
            return "A"
        elif pass_rate > 0.90:
            return "B"
        elif pass_rate > 0.80:
            return "C"
        else:
            return "F"

    async def process_certification_run(self, payload: Dict[str, Any]) -> CertificationRun:
        run_id = payload.get("run_id")
        cert_type = payload.get("certification_type", "NIGHTLY")
        runner_version = payload.get("certification_runner_version", "1.0.0")
        
        # Determine Baseline
        baseline_run = await self.get_latest_successful_run(cert_type)
        baseline_run_id = baseline_run.run_id if baseline_run else None

        # Process Evidences
        evidences_data = payload.get("evidences", [])
        
        passed_count = 0
        failed_count = 0
        total_count = len(evidences_data)
        sla_failures = 0
        
        evidences: List[CertificationScenarioEvidence] = []
        
        for ev in evidences_data:
            scenario_id = ev.get("scenario_id")
            correlation_id = ev.get("correlation_id")
            
            det_sec = ev.get("detection_seconds", 0)
            rec_sec = ev.get("recovery_seconds", 0)
            rc_sec = ev.get("root_cause_seconds", 0)
            exp_sec = ev.get("explanation_seconds", 0)
            
            event_loss = ev.get("event_loss", False)
            proj_consist = ev.get("projection_consistent", True)
            chain_complete = ev.get("chain_complete", False)
            
            # Simple SLA logic
            sla_passed = True
            
            # If there's an actual failure detected in the chain
            if not chain_complete or event_loss or not proj_consist:
                sla_passed = False
                
            # If recovery took longer than 60 seconds (example SLA)
            if rec_sec > 60:
                sla_passed = False
                
            if sla_passed:
                passed_count += 1
            else:
                failed_count += 1
                sla_failures += 1
                
            evidence_model = CertificationScenarioEvidence(
                scenario_id=scenario_id,
                correlation_id=correlation_id,
                detection_seconds=det_sec,
                recovery_seconds=rec_sec,
                root_cause_seconds=rc_sec,
                explanation_seconds=exp_sec,
                event_loss=event_loss,
                projection_consistent=proj_consist,
                chain_complete=chain_complete,
                sla_passed=sla_passed
            )
            evidences.append(evidence_model)
            
        grade = self.calculate_grade(passed_count, total_count, sla_failures)
        
        # Create Run Ledger Entry
        started_at = payload.get("started_at")
        if started_at:
            started_at = datetime.fromisoformat(started_at)
        else:
            started_at = datetime.now(timezone.utc)
            
        completed_at = payload.get("completed_at")
        if completed_at:
            completed_at = datetime.fromisoformat(completed_at)
        else:
            completed_at = datetime.now(timezone.utc)
            
        duration = (completed_at - started_at).total_seconds()
            
        run = CertificationRun(
            run_id=run_id,
            certification_type=cert_type,
            certification_runner_version=runner_version,
            baseline_run_id=baseline_run_id,
            started_at=started_at,
            completed_at=completed_at,
            passed=passed_count,
            failed=failed_count,
            total_scenarios=total_count,
            duration_seconds=duration,
            grade=grade,
            evidences=evidences
        )
        
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        
        return run
