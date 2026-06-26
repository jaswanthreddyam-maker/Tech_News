from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.telemetry import TimelineNode, RootCauseAnalysis, RootCauseTimeline
from app.services.root_cause.rules import BaseRootCauseRule, CQRSProjectionLagRule, WorkerOfflineRule, ThumbnailFailureRule, RedisTimeoutRule, QueueSaturationRule
import logging

logger = logging.getLogger(__name__)

class RootCauseAnalyzer:
    """
    Sprint 5.0 Deterministic Engine.
    Consumes a Timeline correlation_id, evaluates it against a registry of rules,
    and produces a definitive RootCauseAnalysis record with calculated confidence.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.rules: list[BaseRootCauseRule] = [
            CQRSProjectionLagRule(),
            WorkerOfflineRule(),
            ThumbnailFailureRule(),
            RedisTimeoutRule(),
            QueueSaturationRule()
        ]

    async def analyze(self, correlation_id: str) -> RootCauseAnalysis:
        logger.info(f"RootCauseAnalyzer evaluating timeline: {correlation_id}")
        
        # 1. Fetch Timeline
        import asyncio
        nodes = []
        for _ in range(5):
            stmt = select(TimelineNode).where(TimelineNode.correlation_id == correlation_id).order_by(TimelineNode.id.asc())
            res = await self.session.execute(stmt)
            nodes = res.scalars().all()
            if nodes:
                break
            await asyncio.sleep(1.0)
            # Need to commit/rollback to refresh SQLite read snapshot
            await self.session.rollback()

        if not nodes:
            logger.warning(f"No TimelineNodes found for {correlation_id}")
            return None
            
        # 2. Ensure RootCauseTimeline parent exists (Creates the Incident wrapper)
        rc_timeline_stmt = select(RootCauseTimeline).where(RootCauseTimeline.correlation_id == correlation_id)
        rc_timeline = (await self.session.execute(rc_timeline_stmt)).scalar_one_or_none()
        
        if not rc_timeline:
            rc_timeline = RootCauseTimeline(
                correlation_id=correlation_id,
                root_event_id=nodes[0].id,
                status="unresolved"
            )
            self.session.add(rc_timeline)
            await self.session.commit()
            await self.session.refresh(rc_timeline)
            
        # 3. Evaluate Rules
        best_match = None
        for rule in self.rules:
            result = rule.evaluate(nodes)
            if result.is_match:
                if not best_match or result.confidence_score > best_match.confidence_score:
                    best_match = result
                    
        if not best_match:
            # Fallback if no specific rule matches
            best_match = RootCauseAnalyzer._create_fallback_match(nodes)
            
        # 4. Save RootCauseAnalysis
        analysis = RootCauseAnalysis(
            correlation_id=correlation_id,
            timeline_id=rc_timeline.id,
            root_cause=best_match.root_cause,
            analysis_version="v1-rule-engine",
            confidence_score=best_match.confidence_score,
            confidence_factors=[f.to_dict() for f in best_match.factors],
            status=best_match.status,
            generated_by="RULE_ENGINE"
        )
        self.session.add(analysis)
        
        # Sync the Incident Timeline wrapper status
        rc_timeline.status = best_match.status
        
        await self.session.commit()
        await self.session.refresh(analysis)
        
        logger.info(f"RootCauseAnalysis generated for {correlation_id} -> {analysis.root_cause} ({analysis.confidence_score})")
        return analysis

    @staticmethod
    def _create_fallback_match(nodes) -> "RuleEvaluationResult":
        from app.services.root_cause.rules import RuleEvaluationResult, ConfidenceFactor
        
        has_failed = any("Failed" in n.title for n in nodes)
        status = "MANUAL_REQUIRED" if has_failed else "OPEN"
        
        return RuleEvaluationResult(
            is_match=True,
            root_cause="Unknown System Degradation",
            confidence_score=0.1,
            factors=[ConfidenceFactor(evidence="No deterministic rule matched the timeline", weight=0.1)],
            status=status
        )
