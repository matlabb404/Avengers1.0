"""
Refresh-token service: opaque tokens, hashed at rest, rotated on every use, with
family-based reuse detection.

Flow:
  * On login  -> create_refresh_token() mints a new family (new family_id).
  * On refresh -> verify_and_rotate() checks the presented token:
        - not found            -> invalid (401)
        - expired              -> invalid (401)
        - revoked (reuse!)     -> SECURITY: revoke the whole family, invalid (401)
        - valid                -> mint a new token in the SAME family, mark old
                                  revoked + replaced_by, return the new one.
  * On logout -> revoke_token() revokes the presented refresh token (and family).
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models.account_model import RefreshToken

# 30-day refresh lifetime. Move to settings if you want it configurable.
REFRESH_TOKEN_TTL_DAYS = 30
# Length of the opaque token (bytes -> ~43 urlsafe chars for 32 bytes).
_TOKEN_BYTES = 32


def _hash(token: str) -> str:
    """SHA-256 hex of the opaque token. What we store and look up by."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_opaque_token() -> str:
    """A cryptographically-random, URL-safe opaque token (not a JWT)."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def create_refresh_token(
    db: Session,
    user_id,
    *,
    family_id: Optional[uuid.UUID] = None,
    user_agent: Optional[str] = None,
    created_ip: Optional[str] = None,
    commit: bool = True,
) -> str:
    """
    Mint a new refresh token for user_id. If family_id is None, starts a new family
    (fresh login). Returns the PLAINTEXT opaque token (the only time it exists in
    plaintext — the caller sends it to the client; we store only the hash).
    """
    token = _new_opaque_token()
    row = RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id,
        token_hash=_hash(token),
        family_id=family_id or uuid.uuid4(),
        issued_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        revoked=False,
        user_agent=user_agent,
        created_ip=created_ip,
    )
    db.add(row)
    if commit:
        db.commit()
    return token


def _find(db: Session, token: str) -> Optional[RefreshToken]:
    return (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == _hash(token))
        .first()
    )


def revoke_family(db: Session, family_id, *, commit: bool = True) -> int:
    """Revoke every non-revoked token in a family. Returns count revoked."""
    now = datetime.now(timezone.utc)
    n = (
        db.query(RefreshToken)
        .filter(RefreshToken.family_id == family_id, RefreshToken.revoked.is_(False))
        .update({RefreshToken.revoked: True, RefreshToken.revoked_at: now},
                synchronize_session=False)
    )
    if commit:
        db.commit()
    return n


def revoke_token(db: Session, token: str, *, commit: bool = True) -> bool:
    """
    Revoke a single presented refresh token (used on logout). Also revokes its
    family, so logging out kills every rotation descendant. Returns True if found.
    """
    row = _find(db, token)
    if row is None:
        return False
    revoke_family(db, row.family_id, commit=commit)
    return True


def verify_and_rotate(
    db: Session,
    token: str,
    *,
    user_agent: Optional[str] = None,
    created_ip: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Verify a presented refresh token and rotate it.

    Returns (new_refresh_token, user_email) on success, or (None, None) on any
    failure (not found / expired / reuse). On REUSE (a revoked token presented),
    revokes the whole family as a theft response.

    The caller mints a fresh ACCESS token from user_email separately.
    """
    row = _find(db, token)
    if row is None:
        return None, None

    now = datetime.now(timezone.utc)

    # Reuse detection: a revoked token being presented means either a race or theft.
    # Nuke the family so neither the attacker nor the victim can keep using it.
    if row.revoked:
        revoke_family(db, row.family_id, commit=True)
        return None, None

    # Expired.
    if row.expires_at <= now:
        return None, None

    # Valid -> rotate: mint a new token in the same family, revoke this one.
    from app.models.account_model import User
    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None:
        return None, None

    new_token = create_refresh_token(
        db, row.user_id, family_id=row.family_id,
        user_agent=user_agent, created_ip=created_ip, commit=False,
    )
    # Link + revoke the old row.
    new_row = _find(db, new_token)
    row.revoked = True
    row.revoked_at = now
    row.replaced_by = new_row.id if new_row else None
    db.commit()

    return new_token, user.email