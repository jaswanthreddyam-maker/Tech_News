import logging
import statistics
from typing import Any

logger = logging.getLogger(__name__)

class AnomalyAnalysisCapability:
    """
    Deterministic capability for detecting statistical anomalies.
    Does NOT use an LLM. Pure mathematics only.
    """

    async def analyze(self, metrics: list[dict[str, Any]], target_metric: str) -> dict[str, Any]:
        logger.info(f"AnomalyAnalysisCapability analyzing {len(metrics)} points for {target_metric}")

        values = [m["value"] for m in metrics if m["metric"] == target_metric]
        if len(values) < 3:
            return {"anomaly": False, "reason": "Insufficient data"}

        # Very simple baseline calculation (e.g., median of all but last 2)
        baseline_values = values[:-2]
        if not baseline_values:
            baseline_values = values

        baseline_median = statistics.median(baseline_values)
        current_value = values[-1]

        if baseline_median == 0:
            deviation = 0
        else:
            deviation = ((current_value - baseline_median) / baseline_median) * 100

        # Threshold: 100% deviation
        is_anomaly = deviation > 100

        return {
            "anomaly": is_anomaly,
            "metric": target_metric,
            "baseline": baseline_median,
            "current": current_value,
            "deviation": deviation,
            "confidence": 0.98 if is_anomaly else 0.0,
            "evidence": metrics[-3:] # Last 3 points
        }
