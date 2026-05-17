"""
Tiny in-process event bus.

Pattern:
- Modules emit named events with a payload
- Subscribers (handlers) register via @subscribe decorator
- All handlers for an event are awaited in order

Handlers should be small and fast. For heavy work (sending emails, etc.),
the handler should enqueue to a background task.

Failure isolation: one handler crashing does NOT prevent others from running,
but the error IS logged so it's visible.
"""
import asyncio
import logging
from collections import defaultdict
from typing import Any, Awaitable, Callable, Dict, List


logger = logging.getLogger(__name__)

# event_name -> list of async handlers
_handlers: Dict[str, List[Callable[[dict], Awaitable[Any]]]] = defaultdict(list)


def subscribe(event_name: str):
    """
    Decorator to register an async handler for an event.
    
    Usage:
        @subscribe("payment.succeeded")
        async def notify_vendor(payload: dict):
            booking_id = payload["booking_id"]
            ...
    """
    def decorator(handler: Callable[[dict], Awaitable[Any]]):
        _handlers[event_name].append(handler)
        logger.debug(f"Subscribed {handler.__name__} to '{event_name}'")
        return handler
    return decorator


async def emit(event_name: str, payload: dict) -> None:
    """
    Emit an event. All registered handlers run concurrently.
    A handler raising does not affect other handlers.
    """
    handlers = _handlers.get(event_name, [])
    
    if not handlers:
        logger.debug(f"Event '{event_name}' emitted with no subscribers")
        return
    
    logger.debug(f"Emitting '{event_name}' to {len(handlers)} handler(s)")
    
    # Run all handlers concurrently, catching individual errors
    results = await asyncio.gather(
        *(_safe_invoke(h, event_name, payload) for h in handlers),
        return_exceptions=False,  # Already handled inside _safe_invoke
    )


async def _safe_invoke(handler, event_name: str, payload: dict):
    """Invoke a handler with full error isolation."""
    try:
        await handler(payload)
    except Exception as e:
        logger.exception(
            f"Handler {handler.__name__} failed for event '{event_name}': {e}"
        )


# ────────────────────────────────────────────────────────────
# Event name constants — single source of truth for event names
# ────────────────────────────────────────────────────────────

class Events:
    """All event names. Use these constants instead of bare strings."""
    
    # Payment lifecycle
    PAYMENT_INITIATED = "payment.initiated"
    PAYMENT_SUCCEEDED = "payment.succeeded"
    PAYMENT_FAILED = "payment.failed"
    
    # Booking lifecycle
    BOOKING_CONFIRMED = "booking.confirmed"   # Paid, locked in
    BOOKING_CANCELLED = "booking.cancelled"   # Cancelled by user or system
    BOOKING_COMPLETED = "booking.completed"   # Service delivered (auto, post-appointment)
    BOOKING_EXPIRED = "booking.expired"       # Payment timeout, slot released