import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.event_bus import EVENT_CHANNEL
from app.core.redis import get_redis_client
from app.core.security import get_current_user_optional
from app.models.user import User

logger = logging.getLogger("tech_news.events")
router = APIRouter()


@router.get("/stream")
async def sse_event_stream(
    request: Request,
    token: str | None = Query(None, description="Optional JWT authentication token"),
):
    """
    Server-Sent Events stream of real pipeline agent events.
    Subscribes to Redis pub/sub and forwards events to connected clients.
    """
    auth_header = request.headers.get("Authorization")
    user_token = token
    if not user_token and auth_header and auth_header.startswith("Bearer "):
        user_token = auth_header.split(" ", 1)[1]

    if user_token:
        from app.core.security import decode_access_token
        try:
            decode_access_token(user_token)
        except Exception as e:
            logger.warning(f"Events SSE: Invalid token provided ({e}), proceeding as guest stream.")

    async def event_generator():
        from app.core.shutdown import shutdown_event

        client = get_redis_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(EVENT_CHANNEL)
        logger.info("Events SSE: Client subscribed to agent event stream.")

        try:
            while not shutdown_event.is_set():
                if await request.is_disconnected():
                    logger.info("Events SSE: Client disconnected via request check.")
                    break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
                else:
                    # Send keepalive comment every iteration to detect disconnects
                    yield f": keepalive {datetime.now(timezone.utc).strftime('%H:%M:%S')}\n\n"
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info("Events SSE: Client disconnected (CancelledError).")
        except Exception as e:
            logger.error(f"Events SSE: Error in stream: {e}")
        finally:
            try:
                await pubsub.unsubscribe(EVENT_CHANNEL)
                await pubsub.aclose()
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
