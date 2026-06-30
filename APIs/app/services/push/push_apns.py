"""
APNs HTTP/2 sender — iOS push, direct to Apple, ZERO Firebase. We:

  1. Self-sign an ES256 JWT with an APNs Auth Key (.p8) downloaded from the Apple
     Developer portal (Keys -> create a key with APNs enabled). Claims: iss = your
     Apple Team ID, kid = the key id, iat = now. Cached ~50 min (Apple requires the
     token be 20-60 min old; we refresh well within that).
  2. POST the payload to Apple's APNs endpoint over HTTP/2:
       prod: https://api.push.apple.com/3/device/{token}
       dev:  https://api.sandbox.push.apple.com/3/device/{token}
     with headers: authorization: bearer <jwt>, apns-topic: <bundle id>,
     apns-push-type: alert, apns-priority: 10.

APNs uses HTTP/2 — httpx must be built with http2=True (pip install 'httpx[http2]'
or pip install h2).

Settings used:
  APNS_AUTH_KEY_PATH   - path to the .p8 file
  APNS_KEY_ID          - the Key ID (kid)
  APNS_TEAM_ID         - your Apple Team ID (iss)
  APNS_BUNDLE_ID       - the app bundle id (apns-topic)
  APNS_USE_SANDBOX     - bool; True for dev builds, False for App Store/TestFlight prod

Deps: pip install pyjwt cryptography 'httpx[http2]'

Place at: app/services/push/push_apns.py
"""
import time
import json
import logging
from typing import Optional

import httpx
import jwt  # PyJWT (ES256 needs cryptography installed)

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_APNS_PROD = "https://api.push.apple.com/3/device/{token}"
_APNS_SANDBOX = "https://api.sandbox.push.apple.com/3/device/{token}"

_auth_jwt: Optional[str] = None
_auth_jwt_iat: float = 0.0

# A single reusable HTTP/2 client (APNs prefers a long-lived connection).
_client: Optional[httpx.Client] = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(http2=True, timeout=10.0)
    return _client


def _auth_key() -> str:
    with open(settings.APNS_AUTH_KEY_PATH, "r") as f:
        return f.read()


def _mint_jwt() -> str:
    """
    ES256 JWT signed with the .p8 key. Reused for ~50 min (Apple wants 20-60 min).
    """
    global _auth_jwt, _auth_jwt_iat
    now = time.time()
    if _auth_jwt and (now - _auth_jwt_iat) < 3000:  # 50 min
        return _auth_jwt

    token = jwt.encode(
        {"iss": settings.APNS_TEAM_ID, "iat": int(now)},
        _auth_key(),
        algorithm="ES256",
        headers={"kid": settings.APNS_KEY_ID},
    )
    _auth_jwt = token
    _auth_jwt_iat = now
    return token


def build_payload(title: str, body: str, data: dict | None = None,
                  badge: int | None = None) -> dict:
    """
    APNs payload. `aps.alert` renders the notification; `aps.badge` sets the app
    icon badge (iOS-specific); custom keys (routing) sit alongside `aps`.
    """
    aps = {
        "alert": {"title": title, "body": body},
        "sound": "default",
    }
    if badge is not None:
        aps["badge"] = badge
    payload = {"aps": aps}
    for k, v in (data or {}).items():
        if v is not None:
            payload[k] = str(v)
    return payload


class ApnsResult:
    def __init__(self, ok: bool, token: str, should_prune: bool = False, error: str | None = None):
        self.ok = ok
        self.token = token
        self.should_prune = should_prune
        self.error = error


def send(token: str, title: str, body: str, data: dict | None = None,
         badge: int | None = None) -> ApnsResult:
    """
    Send one alert to one APNs (iOS) device token. Returns ApnsResult; should_prune
    True when APNs reports the token is invalid (BadDeviceToken/Unregistered).
    """
    try:
        jwt_token = _mint_jwt()
    except Exception as e:
        logger.exception("APNs JWT mint failed")
        return ApnsResult(ok=False, token=token, error=f"auth: {e}")

    base = _APNS_SANDBOX if getattr(settings, "APNS_USE_SANDBOX", False) else _APNS_PROD
    url = base.format(token=token)
    payload = build_payload(title, body, data, badge)

    headers = {
        "authorization": f"bearer {jwt_token}",
        "apns-topic": settings.APNS_BUNDLE_ID,
        "apns-push-type": "alert",
        "apns-priority": "10",
    }

    try:
        resp = _get_client().post(url, headers=headers, content=json.dumps(payload))
    except Exception as e:
        logger.warning("APNs send transport error: %r", e)
        return ApnsResult(ok=False, token=token, error=str(e))

    if resp.status_code == 200:
        return ApnsResult(ok=True, token=token)

    # APNs returns a JSON body with a `reason` on failure.
    prune = False
    reason = ""
    try:
        reason = resp.json().get("reason", "")
    except Exception:
        reason = resp.text[:200]

    # Dead-token reasons -> prune.
    if reason in ("BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"):
        prune = True
    if resp.status_code == 410:  # 410 Gone = Unregistered
        prune = True

    logger.info("APNs send non-200 (%s) reason=%s prune=%s", resp.status_code, reason, prune)
    return ApnsResult(ok=False, token=token, should_prune=prune, error=reason)