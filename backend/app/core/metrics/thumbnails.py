from prometheus_client import Counter, Histogram
from app.core.metrics.registry import REGISTRY

class ThumbnailMetrics:
    def __init__(self, registry):
        self.success_total = Counter(
            "tnt_thumbnail_success_total",
            "Total number of successfully extracted thumbnails",
            registry=registry
        )
        self.failure_total = Counter(
            "tnt_thumbnail_failure_total",
            "Total number of failed thumbnail extractions",
            registry=registry
        )
        self.latency_seconds = Histogram(
            "tnt_thumbnail_latency_seconds",
            "Latency of extracting a thumbnail",
            registry=registry
        )

thumbnail_metrics = ThumbnailMetrics(REGISTRY)
