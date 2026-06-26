import asyncio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
import logging

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/editorial/events", tags=["Admin Editorial Events"])

async def event_generator():
    """Generates SSE events by subscribing to the Redis editorial_events channel."""
    redis = get_redis_client()
    pubsub = redis.pubsub()
    
    await pubsub.subscribe("editorial_events")
    logger.info("Subscribed to editorial_events channel for SSE stream.")
    
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                data = message["data"].decode("utf-8")
                # Format as Server-Sent Event
                yield f"data: {data}\n\n"
            else:
                # Keep-alive heartbeat every 15 seconds could go here if needed, 
                # but relying on timeout loop is fine for now
                await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        logger.info("SSE client disconnected.")
    finally:
        await pubsub.unsubscribe("editorial_events")
        await pubsub.close()

@router.get("", response_class=StreamingResponse)
async def stream_editorial_events():
    """
    SSE Endpoint for Real-Time Editorial Intelligence.
    Streams actionable events like StoryReawakened, CoverageGapDetected, AssignmentReviewCreated.
    """
    return StreamingResponse(event_generator(), media_type="text/event-stream")
