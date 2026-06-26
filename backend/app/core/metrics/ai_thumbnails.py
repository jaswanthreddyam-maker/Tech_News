from prometheus_client import Counter, Histogram

tnt_ai_thumbnail_requests_total = Counter(
    "tnt_ai_thumbnail_requests_total",
    "Total AI thumbnail generation requests",
    ["reason"],
)

tnt_ai_thumbnail_success_total = Counter(
    "tnt_ai_thumbnail_success_total",
    "Successful AI thumbnail generations",
)

tnt_ai_thumbnail_failure_total = Counter(
    "tnt_ai_thumbnail_failure_total",
    "Failed AI thumbnail generations",
    ["error_type"],
)

tnt_ai_thumbnail_rejected_total = Counter(
    "tnt_ai_thumbnail_rejected_total",
    "Rejected AI thumbnail generations (e.g. low confidence, forbidden category)",
    ["reason"],
)

tnt_ai_thumbnail_provider_unavailable_total = Counter(
    "tnt_ai_thumbnail_provider_unavailable_total",
    "Count of provider unavailability errors during AI generation",
    ["provider_name"],
)

tnt_ai_thumbnail_duration_seconds = Histogram(
    "tnt_ai_thumbnail_duration_seconds",
    "Duration of AI thumbnail generation",
)
