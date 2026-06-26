from prometheus_client import Counter
from app.core.metrics.registry import REGISTRY

# Newsletter Subscription Metrics
tnt_newsletter_subscribe_total = Counter(
    "tnt_newsletter_subscribe_total",
    "Total number of newsletter subscription attempts",
    ["source"],
    registry=REGISTRY
)

tnt_newsletter_duplicate_total = Counter(
    "tnt_newsletter_duplicate_total",
    "Total number of duplicate subscription attempts",
    ["source"],
    registry=REGISTRY
)

tnt_newsletter_failure_total = Counter(
    "tnt_newsletter_failure_total",
    "Total number of failed subscription attempts",
    ["source", "reason"],
    registry=REGISTRY
)
