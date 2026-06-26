import logging
from typing import Any

logger = logging.getLogger(__name__)

class TelemetryCapability:
    """
    Exposes raw OS metrics to applications over the capability bus.
    Applications never read the database directly.
    """
    def __init__(self, metrics_repository):
        self.metrics_repository = metrics_repository

    async def get_metrics(self, time_window_seconds: int = 3600) -> list[dict[str, Any]]:
        logger.info(f"TelemetryCapability fetching metrics for last {time_window_seconds}s")
        # In a real implementation, this queries the underlying timeseries DB
        # Returning dummy data for the purpose of the OS mock
        return [
            {"timestamp": "2026-06-14T10:00:00Z", "metric": "planner_latency", "value": 140},
            {"timestamp": "2026-06-14T10:01:00Z", "metric": "planner_latency", "value": 145},
            {"timestamp": "2026-06-14T10:02:00Z", "metric": "planner_latency", "value": 412}, # Anomaly
            {"timestamp": "2026-06-14T10:03:00Z", "metric": "planner_latency", "value": 450}, # Anomaly
        ]
