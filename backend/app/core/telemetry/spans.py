from enum import Enum


class SpanType(str, Enum):
    """
    Standardized span types matching OpenTelemetry concepts.
    Used to categorize traces across the platform for Jaeger/Grafana.
    """
    WORKFLOW = "workflow"          # The overarching execution
    PLANNER = "planner"            # A specific planner generating a DAG
    CAPABILITY = "capability"      # A capability bus invocation
    PROVIDER = "provider"          # An external data provider fetch
    LLM = "llm"                    # A call through the InferenceGateway
    VALIDATOR = "validator"        # A validation or normalization step
    STORAGE = "storage"            # A read/write to Postgres/Redis/Neo4j
    EVENT_DISPATCH = "dispatch"    # Background event bus dispatcher
