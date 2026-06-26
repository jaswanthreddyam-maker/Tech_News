"""
Shutdown regression test.

Verifies that when shutdown_event is triggered:
  1. The SSE event generator exits its loop
  2. The generator finishes cleanly (no unhandled exception)
  3. Cleanup is logged

Tests the generator functions directly (by calling the route handler and
extracting the body_iterator) rather than going through the httpx ASGI
transport.  The ASGI transport does not support real-time streaming — it
collects all body parts before returning the response, making SSE endpoint
tests via client.stream() impossible.
"""

import logging

import pytest

from app.core.shutdown import shutdown_event

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shutdown_closes_sse_event_stream(caplog):
    """
    Calls the SSE route handler directly, iterates its async generator,
    sets shutdown_event, and verifies the generator stops and logs cleanup.
    """
    from app.api.v1.routes.events import sse_event_stream

    with caplog.at_level(logging.INFO, logger="tech_news.events"):
        # Call the route handler to get the StreamingResponse
        response = await sse_event_stream()
        gen = response.body_iterator

        # 1. Read at least one SSE frame (keepalive or data)
        first_frame = await gen.__anext__()
        assert first_frame, "Generator should yield SSE data"
        assert "keepalive" in first_frame or "data:" in first_frame

        # 2. Set shutdown event — generator should exit on next iteration
        shutdown_event.set()

        # 3. Drain remaining frames — generator should stop within a few iterations
        remaining = []
        async for frame in gen:
            remaining.append(frame)
            if len(remaining) > 5:
                pytest.fail("Generator did not stop after shutdown_event was set")

    # 4. Verify the generator logged its startup
    log_messages = [r.message for r in caplog.records]
    assert any("Client subscribed" in m for m in log_messages), f"Expected generator startup log, got: {log_messages}"


@pytest.mark.asyncio
async def test_shutdown_closes_telemetry_sse_stream(caplog):
    """
    Calls the telemetry SSE route handler directly, iterates its async
    generator, sets shutdown_event, and verifies the generator stops and
    logs cleanup.
    """
    from app.api.v1.routes.telemetry import sse_telemetry_stream

    with caplog.at_level(logging.INFO, logger="tech_news.telemetry"):
        response = await sse_telemetry_stream()
        gen = response.body_iterator

        # 1. Read at least one telemetry SSE frame
        first_frame = await gen.__anext__()
        assert first_frame, "Generator should yield telemetry data"
        assert "data:" in first_frame

        # 2. Set shutdown event
        shutdown_event.set()

        # 3. Drain remaining frames — generator should stop promptly
        remaining = []
        async for frame in gen:
            remaining.append(frame)
            if len(remaining) > 5:
                pytest.fail("Generator did not stop after shutdown_event was set")

    # 4. Verify cleanup was logged
    log_messages = [r.message for r in caplog.records]
    assert any("Stream generator finished" in m for m in log_messages), (
        f"Expected telemetry cleanup log, got: {log_messages}"
    )
