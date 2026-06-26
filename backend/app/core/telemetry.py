import logging

logger = logging.getLogger(__name__)

def track_event(event_name: str, payload: dict | None = None):
    logger.info(f"Telemetry Event: {event_name}", extra={"payload": payload})
