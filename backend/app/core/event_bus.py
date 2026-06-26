import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("tech_news.event_bus")

# Channel name for agent events
EVENT_CHANNEL = "agent_events"


async def publish_event(agent: str, message: str, status: str = "info", metadata: dict | None = None):
    """
    Publish a real pipeline event to Redis pub/sub.
    Events are consumed by the SSE /events/stream endpoint.
    """
    try:
        from app.core.redis import get_redis_client

        client = get_redis_client()
        event = {
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "agent": agent,
            "msg": message,
            "status": status,
        }
        if metadata:
            event["meta"] = metadata
        event_str = json.dumps(event)

        # Publish to SSE Pub/Sub
        await client.publish(EVENT_CHANNEL, event_str)

        # Cache in a rolling list of the last 50 events
        await client.lpush("recent_events", event_str)
        await client.ltrim("recent_events", 0, 49)
    except Exception as e:
        logger.warning(f"EventBus: Failed to publish event: {e}")
