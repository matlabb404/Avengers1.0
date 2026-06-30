"""
Device-token management: register (upsert), unregister, lookup for sending, and
prune. The push transports (FCM/APNs) call get_user_tokens() to find where to send
and delete_token() to prune ones the providers reject.
"""
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.device_token_model import DeviceToken, DevicePlatform


def register_token(db: Session, user_id: UUID, token: str, platform: str) -> bool:
    """
    Upsert a device token. If the token already exists (any user), re-point it at
    this user and bump last_seen_at — handles OS token reassignment and reinstalls.
    Idempotent.
    """
    platform = (platform or "").upper()
    if platform not in DevicePlatform.ALL:
        raise ValueError(f"Unknown platform: {platform}")

    existing = db.query(DeviceToken).filter(DeviceToken.token == token).first()
    if existing is not None:
        existing.user_id = user_id
        existing.platform = platform
        existing.last_seen_at = datetime.now(timezone.utc)
        db.commit()
        return True

    row = DeviceToken(user_id=user_id, token=token, platform=platform,
                      last_seen_at=datetime.now(timezone.utc))
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Race: another request inserted the same token between our check and insert.
        db.rollback()
        existing = db.query(DeviceToken).filter(DeviceToken.token == token).first()
        if existing is not None:
            existing.user_id = user_id
            existing.platform = platform
            existing.last_seen_at = datetime.now(timezone.utc)
            db.commit()
    return True


def unregister_token(db: Session, user_id: UUID, token: str) -> bool:
    """Remove a token (logout / app uninstall signal). Only the owner can remove it."""
    deleted = (
        db.query(DeviceToken)
        .filter(DeviceToken.token == token, DeviceToken.user_id == user_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return bool(deleted)


def get_user_tokens(db: Session, user_id: UUID) -> List[DeviceToken]:
    """All device tokens for a user (used by the push dispatcher)."""
    return db.query(DeviceToken).filter(DeviceToken.user_id == user_id).all()


def get_tokens_for_users(db: Session, user_ids) -> List[DeviceToken]:
    """Bulk token lookup for many recipients (used by fan-out push)."""
    if not user_ids:
        return []
    return db.query(DeviceToken).filter(DeviceToken.user_id.in_(user_ids)).all()


def delete_token(db: Session, token: str) -> None:
    """Prune a single token (called when FCM/APNs reports it's dead/unregistered)."""
    db.query(DeviceToken).filter(DeviceToken.token == token).delete(
        synchronize_session=False
    )
    db.commit()