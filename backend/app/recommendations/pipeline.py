import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.recommendations.capability import recommendation_registry
from app.recommendations.diversifier import RecommendationDiversifier
from app.recommendations.filters import get_filters
from app.recommendations.schemas import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationTelemetry,
)

logger = logging.getLogger(__name__)

class RecommendationPipeline:
    pipeline_version = "1.0"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def run(self, request: RecommendationRequest) -> RecommendationResponse:
        start_time = time.time()
        telemetry = RecommendationTelemetry(
            pipeline_stage="START",
            strategy=request.strategy,
            candidate_count=0,
            filtered_count=0
        )

        capability = recommendation_registry.get(request.strategy)
        if not capability:
            logger.error(f"Strategy {request.strategy} not found in registry")
            return RecommendationResponse(
                request_id=request.request_id,
                strategy=request.strategy,
                latency_ms=(time.time() - start_time) * 1000,
                candidate_count=0,
                candidates=[],
                telemetry=telemetry
            )

        if not capability.supports(request):
            logger.warning(f"Strategy {request.strategy} does not support this context")
            return RecommendationResponse(
                request_id=request.request_id,
                strategy=request.strategy,
                latency_ms=(time.time() - start_time) * 1000,
                candidate_count=0,
                candidates=[],
                telemetry=telemetry
            )

        # 1. Retrieve
        step_start = time.time()
        candidates = await capability.retrieve_candidates(request, self.session)
        telemetry.retriever_latency_ms = (time.time() - step_start) * 1000
        telemetry.candidate_count = len(candidates)

        # 2. Validate
        step_start = time.time()
        valid_candidates = []
        for c in candidates:
            # Simple validation to catch missing IDs or malformed items
            if c.article_id and isinstance(c.features, dict):
                valid_candidates.append(c)
        telemetry.validator_latency_ms = (time.time() - step_start) * 1000
        candidates = valid_candidates

        # 3. Filter
        step_start = time.time()
        filters = get_filters(request.filters)
        filtered_candidates = []
        for c in candidates:
            passed = True
            for f in filters:
                if f.supports(request) and not await f.apply(c, request, self.session):
                    passed = False
                    break
            if passed:
                filtered_candidates.append(c)

        telemetry.filtered_count = len(candidates) - len(filtered_candidates)
        candidates = filtered_candidates
        telemetry.filter_latency_ms = (time.time() - step_start) * 1000

        # 4. Score
        step_start = time.time()
        candidates = capability.score(candidates, request)
        telemetry.score_latency_ms = (time.time() - step_start) * 1000

        # 5. Sort
        step_start = time.time()
        candidates = capability.sort(candidates, request)
        telemetry.sort_latency_ms = (time.time() - step_start) * 1000

        # 6. Diversify
        step_start = time.time()
        diversifier = RecommendationDiversifier(penalties={"primary_topic": 1.0})
        candidates = diversifier.diversify(candidates, request)
        telemetry.diversifier_latency_ms = (time.time() - step_start) * 1000

        # 7. Explain
        step_start = time.time()
        for i, c in enumerate(candidates):
            explanation = capability.explain(c, request)
            if explanation:
                c.reasons = [explanation]
            c.rank = i + 1
        telemetry.explanation_latency_ms = (time.time() - step_start) * 1000

        # 8. Post-Process
        step_start = time.time()
        candidates = capability.post_process(candidates, request)
        telemetry.postprocess_latency_ms = (time.time() - step_start) * 1000

        # Enforce limit after post processing
        candidates = candidates[:request.limit]

        telemetry.total_latency_ms = (time.time() - start_time) * 1000
        telemetry.pipeline_stage = "COMPLETE"

        logger.info(f"Recommendation complete: {telemetry.model_dump_json()}")

        return RecommendationResponse(
            request_id=request.request_id,
            strategy=request.strategy,
            strategy_version=capability.version,
            latency_ms=telemetry.total_latency_ms,
            candidate_count=len(candidates),
            candidates=candidates,
            telemetry=telemetry,
            metadata={"pipeline_version": self.pipeline_version}
        )
