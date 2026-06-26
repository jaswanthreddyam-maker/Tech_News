from prometheus_client import Counter, Histogram
from app.core.metrics.registry import REGISTRY

class IngestionMetrics:
    def __init__(self, registry):
        self.rss_fetch_duration = Histogram(
            "tnt_rss_fetch_duration_seconds",
            "Latency of fetching an RSS feed",
            registry=registry
        )
        self.rss_fetch_failures = Counter(
            "tnt_rss_fetch_failures_total",
            "Total number of RSS fetch failures",
            registry=registry
        )
        self.articles_ingested_total = Counter( # Added per user recommendation
            "tnt_articles_ingested_total",
            "Total number of raw articles ingested",
            registry=registry
        )
        self.articles_published_total = Counter( # Added per user recommendation
            "tnt_articles_published_total",
            "Total number of articles successfully published after AI processing",
            registry=registry
        )
        self.story_assignment_decisions_total = Counter(
            "tnt_story_assignment_decision_total",
            "Total number of story assignment decisions",
            ["decision"],
            registry=registry
        )

ingestion_metrics = IngestionMetrics(REGISTRY)
