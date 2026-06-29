"""
Notification subscribers for booking/payment lifecycle events.

Listens on the in-process event bus (app.events.bus) and turns booking events into
in-app notifications. Imported once at startup so the @subscribe decorators run and
register the handlers (see main.py note at the bottom).

Handlers are async (the bus awaits them); the actual notification write is sync
SQLAlchemy, so we run it in a thread to avoid blocking the event loop — same
pattern as the media worker. Each handler opens its own short-lived Session.

Events handled (payloads as emitted by payment_module):
  BOOKING_CONFIRMED  {booking_id, user_id, vendor_id, service_id, time_date}
  BOOKING_COMPLETED  {booking_id, user_id, service_id, completed_at}
  BOOKING_EXPIRED    {booking_id, user_id, reason}

Recipient for all three is the CUSTOMER (payload['user_id']). actor is the system
(actor_user_id=None) so the self-notify guard never suppresses these.

Place at: app/events/notification_events.py
"""
import asyncio
import logging

from app.events.bus import subscribe, Events
from app.config.db.postgresql import SessionLocal
from app.modules import notification_module as nm
from app.models.notification_model import NotificationType, NotificationTarget

logger = logging.getLogger(__name__)


def _notify_sync(*, recipient_user_id, ntype, booking_id, preview, vendor_id=None):
    """Open a session and write one notification (sync). Never raises into the bus."""
    db = SessionLocal()
    try:
        nm.notify(
            db,
            recipient_user_id=recipient_user_id,
            type=ntype,
            actor_user_id=None,                  # system-generated
            actor_name=None,
            target_type=NotificationTarget.BOOKING,
            target_id=str(booking_id),
            preview=preview,
            vendor_id=vendor_id,                 # for per-vendor mute (may be None)
            commit=True,
        )
    except Exception:
        logger.exception("notification write failed for booking=%s type=%s", booking_id, ntype)
    finally:
        db.close()


def _to_uuid(val):
    """Payloads stringify ids; convert back to UUID where the column expects it."""
    from uuid import UUID
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, TypeError):
        return val  # leave as-is; PG may still cast


@subscribe(Events.BOOKING_CONFIRMED)
async def on_booking_confirmed(payload: dict):
    """Payment succeeded -> booking confirmed. Tell the customer."""
    await asyncio.to_thread(
        _notify_sync,
        recipient_user_id=_to_uuid(payload.get("user_id")),
        ntype=NotificationType.BOOKING_CONFIRMED,
        booking_id=payload.get("booking_id"),
        preview="Your booking is confirmed",
        vendor_id=_to_uuid(payload.get("vendor_id")),
    )


@subscribe(Events.BOOKING_COMPLETED)
async def on_booking_completed(payload: dict):
    """Appointment ended -> completed. Tell the customer (also unlocks rating)."""
    vendor_id = None  # not in the completed payload; mute check falls back to None
    await asyncio.to_thread(
        _notify_sync,
        recipient_user_id=_to_uuid(payload.get("user_id")),
        ntype=NotificationType.BOOKING_COMPLETED,
        booking_id=payload.get("booking_id"),
        preview="Your booking is complete — you can leave a rating",
        vendor_id=vendor_id,
    )


@subscribe(Events.BOOKING_EXPIRED)
async def on_booking_expired(payload: dict):
    """Unpaid timeout -> slot released. Tell the customer it lapsed."""
    await asyncio.to_thread(
        _notify_sync,
        recipient_user_id=_to_uuid(payload.get("user_id")),
        ntype=NotificationType.BOOKING_CANCELLED,   # expiry is a cancellation flavor
        booking_id=payload.get("booking_id"),
        preview="Your booking expired — payment wasn't completed in time",
        vendor_id=None,
    )