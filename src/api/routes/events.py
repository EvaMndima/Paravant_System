"""Server-Sent Events (SSE) endpoint for real-time dashboard updates.

Provides a streaming endpoint that pushes events to connected clients
using the SSE protocol. Each client gets its own asyncio.Queue subscription
via the EventBus.

SSE Protocol:
- Events are formatted as "data: {json}\n\n"
- Heartbeats sent every 30s as ": heartbeat\n\n" (comment lines)
- Client uses EventSource API for automatic reconnection
- No authentication for MVP (single-user system)

Decision: DEC-2026-02-08-003 - Timezone-aware UTC timestamps
Decision: DEC-2026-02-08-008 - Structured logging
Decision: DEC-2026-01-15-005 - Monolithic architecture (in-process EventBus)
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from src.core.event_bus import EVENT_TYPES, EventBus
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Heartbeat interval (seconds) - keeps connection alive through proxies
_HEARTBEAT_INTERVAL: float = 30.0


# ---------------------------------------------------------------------------
# Module-level dependency injection
# ---------------------------------------------------------------------------

_event_bus: EventBus | None = None


def get_event_bus() -> EventBus | None:
    """Get the EventBus instance.

    Returns:
        EventBus instance or None if not initialized.
    """
    return _event_bus


def init_event_routes(event_bus: EventBus) -> None:
    """Initialize the events router with an EventBus instance.

    Args:
        event_bus: Configured EventBus instance.
    """
    global _event_bus  # noqa: PLW0603
    _event_bus = event_bus
    logger.info("event_routes_initialized")


# ---------------------------------------------------------------------------
# SSE Generator
# ---------------------------------------------------------------------------


async def _event_stream(
    request: Request,
    event_bus: EventBus,
    subscriber_id: str,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for a connected client.

    Yields SSE-formatted event strings. Sends heartbeats every 30s
    to keep the connection alive. Automatically unsubscribes on
    client disconnect.

    Args:
        request: FastAPI request (for disconnect detection).
        event_bus: EventBus instance.
        subscriber_id: Subscriber ID for this client.

    Yields:
        SSE-formatted event strings.
    """
    try:
        # Send initial connection confirmation
        connected_event = {
            "type": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "subscriber_id": subscriber_id,
                "event_types": sorted(EVENT_TYPES),
            },
        }
        yield f"data: {json.dumps(connected_event)}\n\n"

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info(
                    "sse_client_disconnected",
                    subscriber_id=subscriber_id,
                )
                break

            # Wait for next event with heartbeat timeout
            event = await event_bus.get_event(
                subscriber_id, timeout=_HEARTBEAT_INTERVAL
            )

            if event is None:
                # Timeout - send heartbeat comment (keeps connection alive)
                yield ": heartbeat\n\n"
            else:
                # Format as SSE event
                yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"

    except asyncio.CancelledError:
        logger.info("sse_stream_cancelled", subscriber_id=subscriber_id)
    except KeyError:
        # Subscriber was removed (shouldn't happen normally)
        logger.warning("sse_subscriber_lost", subscriber_id=subscriber_id)
    except Exception as e:
        logger.error(
            "sse_stream_error",
            subscriber_id=subscriber_id,
            error=str(e),
            exc_info=True,
        )
    finally:
        # Always clean up subscription
        await event_bus.unsubscribe(subscriber_id)
        logger.info(
            "sse_stream_cleanup",
            subscriber_id=subscriber_id,
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/stream",
    summary="SSE event stream",
    description=(
        "Server-Sent Events stream for real-time dashboard updates. "
        "Connect using EventSource API in the browser. "
        "Heartbeats sent every 30s to keep connection alive."
    ),
)
async def event_stream(request: Request) -> StreamingResponse:
    """SSE event stream endpoint.

    Creates a new EventBus subscription and streams events to the client.
    Automatically cleans up on disconnect.

    Args:
        request: FastAPI request object.

    Returns:
        StreamingResponse with SSE content type.
    """
    if _event_bus is None:
        # Return a one-shot error event if EventBus not initialized
        async def error_stream() -> AsyncGenerator[str, None]:
            error = {
                "type": "error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {"message": "EventBus not initialized"},
            }
            yield f"data: {json.dumps(error)}\n\n"

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    # Subscribe to all event types
    subscriber_id = await _event_bus.subscribe()

    subscriber_count = await _event_bus.get_subscriber_count()
    logger.info(
        "sse_client_connected",
        subscriber_id=subscriber_id,
        total_subscribers=subscriber_count,
    )

    return StreamingResponse(
        _event_stream(request, _event_bus, subscriber_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
