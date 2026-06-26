import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.event_bus import EVENT_CHANNEL
from app.core.redis import get_redis_client
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger("tech_news.events")
router = APIRouter()


@router.get("/stream")
async def sse_event_stream(current_user: User = Depends(get_current_user)):
    """
    Server-Sent Events stream of real pipeline agent events.
    Subscribes to Redis pub/sub and forwards events to connected clients.
    """

    async def event_generator():
        from app.core.shutdown import shutdown_event

        client = get_redis_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(EVENT_CHANNEL)
        logger.info("Events SSE: Client subscribed to agent event stream.")

        try:
            while not shutdown_event.is_set():
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
                else:
                    # Send keepalive comment every iteration to detect disconnects
                    yield f": keepalive {datetime.now(timezone.utc).strftime('%H:%M:%S')}\n\n"
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info("Events SSE: Client disconnected.")
        except Exception as e:
            logger.error(f"Events SSE: Error in stream: {e}")
        finally:
            await pubsub.unsubscribe(EVENT_CHANNEL)
            await pubsub.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
