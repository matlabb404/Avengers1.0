"""
FCM HTTP v1 sender — Android push, fully self-owned (no firebase-admin / google
libs). We:

  1. Self-sign a JWT with the service-account private key (RS256), claiming the
     googleapis token scope.
  2. Exchange it at Google's OAuth2 token endpoint for a short-lived access token
     (cached in-process until ~60s before expiry).
  3. POST the message to
     https://fcm.googleapis.com/v1/projects/{project_id}/messages:send
     with Authorization: Bearer <access_token>.

Credentials come from a service-account JSON (Firebase console -> Project settings
-> Service accounts -> Generate new private key). We read project_id, client_email,
private_key, token_uri from it.

Deps: pip install pyjwt cryptography httpx   (httpx already present)

Place at: app/services/push/push_fcm.py
"""
import json
import time
import logging
from typing import Optional

import httpx
import jwt  # PyJWT

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_GOOGLE_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_FCM_ENDPOINT = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

# Cached service-account dict + access token.
_sa: Optional[dict] = None
_access_token: Optional[str] = None
_access_token_exp: float = 0.0


def _load_sa() -> dict:
    """Load + cache the service-account JSON. Path from settings.FIREBASE_CREDENTIALS_PATH."""
    global _sa
    if _sa is None:
        path = settings.FIREBASE_CREDENTIALS_PATH
        with open(path, "r") as f:
            _sa = json.load(f)
    return _sa


def _mint_access_token() -> str:
    """
    Self-sign a JWT with the SA private key and exchange it for an OAuth2 access
    token. Cached until ~60s before expiry. Fully manual — no google-auth.
    """
    global _access_token, _access_token_exp
    now = time.time()
    if _access_token and now < (_access_token_exp - 60):
        return _access_token

    sa = _load_sa()
    iat = int(now)
    exp = iat + 3600
    payload = {
        "iss": sa["client_email"],
        "scope": _GOOGLE_SCOPE,
        "aud": sa["token_uri"],          # https://oauth2.googleapis.com/token
        "iat": iat,
        "exp": exp,
    }
    # RS256 signed with the SA private key.
    assertion = jwt.encode(payload, sa["private_key"], algorithm="RS256")

    resp = httpx.post(
        sa["token_uri"],
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    _access_token = data["access_token"]
    _access_token_exp = now + int(data.get("expires_in", 3600))
    return _access_token


def build_message(token: str, title: str, body: str, data: dict | None = None) -> dict:
    """
    FCM v1 message. We put the human text in `notification` (so the OS shows it when
    backgrounded) AND mirror routing fields in `data` (so the app can deep-link on
    tap). android.priority high = deliver promptly. data values MUST be strings.
    """
    data_str = {k: str(v) for k, v in (data or {}).items() if v is not None}
    return {
        "message": {
            "token": token,
            "notification": {"title": title, "body": body},
            "data": data_str,
            "android": {
                "priority": "high",
                "notification": {
                    # A click_action / channel can be set here if your app defines one.
                    "default_sound": True,
                },
            },
        }
    }


class FcmResult:
    def __init__(self, ok: bool, token: str, should_prune: bool = False, error: str | None = None):
        self.ok = ok
        self.token = token
        self.should_prune = should_prune   # token is dead -> caller deletes it
        self.error = error


def send(token: str, title: str, body: str, data: dict | None = None) -> FcmResult:
    """
    Send one message to one FCM (Android) token. Returns FcmResult; should_prune is
    True when FCM says the token is unregistered/invalid so the caller deletes it.
    """
    try:
        access_token = _mint_access_token()
    except Exception as e:
        logger.exception("FCM access token mint failed")
        return FcmResult(ok=False, token=token, error=f"auth: {e}")

    sa = _load_sa()
    url = _FCM_ENDPOINT.format(project_id=sa["project_id"])
    msg = build_message(token, title, body, data)

    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=msg,
            timeout=10.0,
        )
    except Exception as e:
        logger.warning("FCM send transport error: %r", e)
        return FcmResult(ok=False, token=token, error=str(e))

    if resp.status_code == 200:
        return FcmResult(ok=True, token=token)

    # Error handling: UNREGISTERED / INVALID_ARGUMENT (bad token) -> prune.
    prune = False
    err_text = resp.text
    try:
        err = resp.json().get("error", {})
        status = err.get("status", "")
        # FCM v1 error statuses for dead tokens:
        if status in ("NOT_FOUND", "UNREGISTERED", "INVALID_ARGUMENT"):
            prune = True
        # 404/UNREGISTERED means the token no longer exists.
        if resp.status_code == 404:
            prune = True
    except Exception:
        pass

    logger.info("FCM send non-200 (%s) prune=%s: %s", resp.status_code, prune, err_text[:200])
    return FcmResult(ok=False, token=token, should_prune=prune, error=err_text[:300])