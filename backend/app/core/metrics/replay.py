from prometheus_client import Counter, Histogram
from app.core.metrics.registry import REGISTRY

class ReplayMetrics:
    def __init__(self, registry):
        self.requests_total = Counter(
            "tnt_replay_requests_total",
            "Total number of replay operations requested",
            ["type"], # Labels: event, projection, batch
            registry=registry
        )
        self.success_total = Counter(
            "tnt_replay_success_total",
            "Total number of successful replay operations",
            ["type"],
            registry=registry
        )
        self.failure_total = Counter(
            "tnt_replay_failure_total",
            "Total number of failed replay operations",
            ["type"],
            registry=registry
        )
        self.duration_seconds = Histogram(
            "tnt_replay_duration_seconds",
            "Latency of a replay operation",
            ["type"],
            registry=registry
        )

replay_metrics = ReplayMetrics(REGISTRY)
