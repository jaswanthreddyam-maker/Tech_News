from prometheus_client import Counter, Histogram
from app.core.metrics.registry import REGISTRY

class RecoveryMetrics:
    def __init__(self, registry):
        self.attempts_total = Counter(
            "tnt_recovery_attempts_total",
            "Total number of autonomous recovery attempts",
            ["type"], # cqrs, thumbnail, queue
            registry=registry
        )
        self.success_total = Counter(
            "tnt_recovery_success_total",
            "Total number of successful autonomous recoveries",
            ["type"],
            registry=registry
        )
        self.failure_total = Counter(
            "tnt_recovery_failure_total",
            "Total number of failed autonomous recoveries",
            ["type"],
            registry=registry
        )
        self.duration_seconds = Histogram(
            "tnt_recovery_duration_seconds",
            "Latency of an autonomous recovery operation",
            ["type"],
            registry=registry
        )

recovery_metrics = RecoveryMetrics(REGISTRY)
