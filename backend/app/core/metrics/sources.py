from prometheus_client import Gauge, Counter
from app.core.metrics.registry import REGISTRY

class SourceMetrics:
    def __init__(self, registry):
        self.health_score = Gauge(
            "tnt_source_health_score",
            "Current health score of a source (0.0 to 1.0)",
            ["source_id"],
            registry=registry
        )

source_metrics = SourceMetrics(REGISTRY)

class HealthMetrics:
    def __init__(self, registry):
        self.checks_failed_total = Counter(
            "tnt_health_checks_failed_total",
            "Total number of internal health checks that failed",
            ["subsystem"],
            registry=registry
        )

health_metrics = HealthMetrics(REGISTRY)
