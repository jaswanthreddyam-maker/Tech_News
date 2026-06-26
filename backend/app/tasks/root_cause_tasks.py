import logging
from celery_app import celery_app, get_celery_session, run_in_worker_loop
from app.services.root_cause.analyzer import RootCauseAnalyzer

logger = logging.getLogger(__name__)

async def analyze_timeline(correlation_id: str):
    """Core async logic for root cause analysis."""
    async with get_celery_session() as db:
        analyzer = RootCauseAnalyzer(db)
        analysis = await analyzer.analyze(correlation_id)
        if analysis:
            # Trigger Sprint 5.1 AI Explanation Layer
            if analysis.confidence_score >= 0.70:
                from app.services.root_cause.explanation.service import LLMExplanationProvider
                explainer = LLMExplanationProvider(db)
                await explainer.generate_explanation(analysis)
            
            return {
                "status": "success",
                "root_cause": analysis.root_cause,
                "confidence": analysis.confidence_score
            }
        return {"status": "no_match"}

@celery_app.task(name="tasks.root_cause.analyze_timeline_task")
def analyze_timeline_task(correlation_id: str):
    """
    Decoupled task that performs root cause analysis on a completed timeline.
    Triggered by RecoveryService after a recovery workflow finishes.
    """
    logger.info(f"Starting root cause analysis task for {correlation_id}")
    try:
        results = run_in_worker_loop(analyze_timeline(correlation_id))
        return results
    except Exception as e:
        logger.error(f"Root Cause Analysis failed for {correlation_id}: {e}")
        return {"status": "error"}
