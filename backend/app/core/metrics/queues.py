from prometheus_client import Gauge, Histogram
from app.core.metrics.registry import REGISTRY

class QueueMetrics:
    def __init__(self, registry):
        self.queue_depth = Gauge(
            "tnt_queue_depth",
            "Current depth of a specific background queue",
            ["queue_name"],
            registry=registry
        )
        self.queue_processing_duration = Histogram(
            "tnt_queue_processing_duration_seconds",
            "Latency of processing a background task",
            ["task_name"],
            registry=registry
        )

queue_metrics = QueueMetrics(REGISTRY)
