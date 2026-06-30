"""
Push dispatcher: turn a stored Notification into platform pushes.

Routes each of the recipient's device tokens to the right transport (ANDROID->FCM,
IOS->APNs), prunes tokens the providers reject, and renders a human title/body +
a data payload (target_type/target_id) for deep-linking on tap.

Called from the arq push task (push_task), which is enqueued by create_notification
when push is enabled. Runs in the worker, sync, its own session.
"""
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.device_token_model import DevicePlatform
from app.modules import device_token_module as dt
from app.services.push import push_fcm, push_apns

logger = logging.getLogger(__name__)


# ── Render a notification type into a title/body ──────────────────────────────

def render(ntype: str, actor_name: str | None, preview: str | None) -> tuple[str, str]:
    """
    Turn (type, actor_name, preview) into (title, body) for the OS notification.
    Falls back gracefully when actor_name/preview are missing.
    """
    who = actor_name or "Someone"
    p = preview or ""

    titles = {
        "LIKE": "New like",
        "COMMENT": "New comment",
        "RATING": "New rating",
        "FOLLOW": "New follower",
        "MESSAGE": who,                       # message shows sender as the title
        "NEW_SERVICE": who,
        "BIG_SERVICE": who,
        "BOOKING_NEW": "New booking",
        "BOOKING_CONFIRMED": "Booking confirmed",
        "BOOKING_CANCELLED": "Booking cancelled",
        "BOOKING_COMPLETED": "Booking complete",
        "BOOKING": "Booking update",
    }
    title = titles.get(ntype, "Notification")

    # Body: prefer the preview; otherwise a sensible default per type.
    if p:
        body = p if ntype == "MESSAGE" else (f"{who} {p}" if who != "Someone" else p)
    else:
        body = {
            "LIKE": f"{who} liked your post",
            "COMMENT": f"{who} commented",
            "FOLLOW": f"{who} started following you",
            "MESSAGE": "New message",
        }.get(ntype, "You have a new notification")

    return title, body


# ── Dispatch ──────────────────────────────────────────────────────────────────

def push_to_user(
    db: Session,
    *,
    recipient_user_id: UUID,
    ntype: str,
    actor_name: str | None = None,
    preview: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
) -> int:
    """
    Send one notification to ALL of a user's devices. Returns count of successful
    sends. Prunes dead tokens. Never raises (push failures must not break callers).
    """
    tokens = dt.get_user_tokens(db, recipient_user_id)
    if not tokens:
        return 0

    title, body = render(ntype, actor_name, preview)
    data = {
        "type": ntype,
        "target_type": target_type or "",
        "target_id": target_id or "",
    }

    sent = 0
    for device in tokens:
        try:
            if device.platform == DevicePlatform.ANDROID:
                res = push_fcm.send(device.token, title, body, data)
            elif device.platform == DevicePlatform.IOS:
                res = push_apns.send(device.token, title, body, data)
            else:
                continue

            if res.ok:
                sent += 1
            elif res.should_prune:
                logger.info("pruning dead token (%s)", device.platform)
                dt.delete_token(db, device.token)
        except Exception:
            logger.exception("push to a device failed (continuing)")

    return sent