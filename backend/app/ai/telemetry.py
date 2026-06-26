from app.ai.cost import calculate_cost_usd
from app.ai.schemas import AIJobStatus, AIProviderResponse, AITelemetryRecord


def telemetry_from_response(
    response: AIProviderResponse,
    *,
    prompt_version: str,
    status: AIJobStatus = AIJobStatus.COMPLETED,
    retry_count: int = 0,
    error: str | None = None,
) -> AITelemetryRecord:
    return AITelemetryRecord(
        provider=response.provider,
        model=response.model,
        task_type=response.task_type,
        prompt_version=prompt_version,
        prompt_hash=response.prompt_hash,
        status=status,
        latency_ms=response.latency_ms,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        total_tokens=response.usage.total_tokens,
        cost_usd=calculate_cost_usd(response.model, response.usage),
        cache_hit=response.cache_hit,
        retry_count=retry_count,
        error=error,
        provider_metadata=response.provider_metadata,
        enrichment_input_fingerprint=response.enrichment_input_fingerprint,
    )
