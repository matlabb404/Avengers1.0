from sqlalchemy import Column, String, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.config.db.postgresql import Base
from app.utils.mixins import TimestampMixin
import uuid


class DevicePlatform:
    ANDROID = "ANDROID"   # FCM token
    IOS = "IOS"           # APNs token
    ALL = (ANDROID, IOS)


class DeviceToken(TimestampMixin, Base):
    """
    A push token for one device of one user. A user can have many (phone, tablet,
    reinstall). The token is UNIQUE across the table — if the same token reappears
    (e.g. an OS reassigns it, or the same device re-registers), we upsert and
    re-point it at the current user.

      platform = ANDROID -> `token` is an FCM registration token (sent via FCM v1)
      platform = IOS     -> `token` is an APNs device token (sent direct to APNs)

    last_seen_at is bumped on every (re)register so we can prune stale tokens later.
    Dead tokens (rejected by FCM/APNs at send time) are deleted by the sender.
    """
    __tablename__ = "device_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token = Column(String, nullable=False, unique=True)
    platform = Column(String, nullable=False)   # DevicePlatform.*
    last_seen_at = Column(
        DateTime, nullable=False, server_default=text("now()")
    )

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_device_tokens_user", "user_id"),
    )