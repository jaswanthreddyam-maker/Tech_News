from prometheus_client import Gauge, Histogram
from app.core.metrics.registry import REGISTRY

class CQRSMetrics:
    def __init__(self, registry):
        self.projection_lag = Gauge(
            "tnt_cqrs_projection_lag",
            "Current difference between processed articles and read-model articles",
            registry=registry
        )
        self.outbox_backlog = Gauge(
            "tnt_cqrs_outbox_backlog",
            "Number of events pending in the outbox",
            registry=registry
        )
        self.projection_duration = Histogram(
            "tnt_cqrs_projection_duration_seconds",
            "Latency of projecting an event to the read model",
            registry=registry
        )
        self.articles_projected_total = Gauge( # Added per user recommendation
            "tnt_articles_projected_total",
            "Total number of articles successfully projected",
            registry=registry
        )
        self.event_replay_total = Gauge( # Added per user recommendation
            "tnt_event_replay_total",
            "Total number of events replayed",
            registry=registry
        )

cqrs_metrics = CQRSMetrics(REGISTRY)
