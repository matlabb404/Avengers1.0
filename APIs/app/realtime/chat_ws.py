import asyncio
import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from redis import asyncio as aioredis

from app.config.db.postgresql import SessionLocal

router = APIRouter()

# ── Redis ─────────────────────────────────────────────────────────────────────
# Reuse the same Redis the arq worker uses. Adjust the URL/settings if your
# RedisSettings differ (e.g. a non-default host/port/db).
REDIS_URL = "redis://localhost:6379/0"
_CHANNEL_PREFIX = "chat:"   # final channel = chat:user:{uuid} / chat:vendor:{uuid}


def _identity_channel(kind: str, ident: UUID | str) -> str:
    return f"{_CHANNEL_PREFIX}{kind}:{ident}"


# ── Connection manager (local sockets on THIS process) ────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        # identity_key ("user:{uuid}" / "vendor:{uuid}") -> set of sockets
        self._sockets: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, identity_key: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._sockets.setdefault(identity_key, set()).add(ws)

    async def disconnect(self, identity_key: str, ws: WebSocket) -> None:
        async with self._lock:
            conns = self._sockets.get(identity_key)
            if conns:
                conns.discard(ws)
                if not conns:
                    self._sockets.pop(identity_key, None)

    async def send_local(self, identity_key: str, payload: str) -> None:
        """Deliver to every local socket for this identity. Prunes dead sockets."""
        conns = list(self._sockets.get(identity_key, ()))
        dead = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(identity_key, ws)

    def has_local(self, identity_key: str) -> bool:
        return bool(self._sockets.get(identity_key))


manager = ConnectionManager()


# ── Redis pub/sub bridge ──────────────────────────────────────────────────────

_redis: Optional[aioredis.Redis] = None
_pubsub_task: Optional[asyncio.Task] = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    return _redis


async def start_pubsub() -> None:
    """Subscribe to the chat channel pattern and fan incoming events out to local
       sockets. One listener per process."""
    global _pubsub_task
    if _pubsub_task is not None:
        return
    _pubsub_task = asyncio.create_task(_pubsub_loop())


async def stop_pubsub() -> None:
    global _pubsub_task, _redis
    if _pubsub_task is not None:
        _pubsub_task.cancel()
        try:
            await _pubsub_task
        except asyncio.CancelledError:
            pass
        _pubsub_task = None
    if _redis is not None:
        await _redis.close()
        _redis = None


async def _pubsub_loop() -> None:
    redis = await _get_redis()
    pubsub = redis.pubsub()
    # Pattern-subscribe to all chat identity channels; we filter by delivering to
    # whichever identity the channel names (only present if connected locally).
    await pubsub.psubscribe(f"{_CHANNEL_PREFIX}*")
    try:
        async for event in pubsub.listen():
            if event is None or event.get("type") != "pmessage":
                continue
            channel: str = event["channel"]
            payload: str = event["data"]
            # channel = chat:user:{uuid} -> identity_key = user:{uuid}
            identity_key = channel[len(_CHANNEL_PREFIX):]
            if manager.has_local(identity_key):
                await manager.send_local(identity_key, payload)
    except asyncio.CancelledError:
        await pubsub.punsubscribe(f"{_CHANNEL_PREFIX}*")
        raise


# ── Publishing (called by the REST send endpoint) ─────────────────────────────

async def publish_new_message(db, conversation_id: UUID, message: dict) -> None:
    """
    Route a freshly-persisted message to the RECIPIENT's identity channel. The
    recipient is the side that did NOT send it.
    `message` is the MessageOut dict from chat_module.send_message().
    """
    from app.models.chat_model import Conversation

    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if convo is None:
        return

    sender_role = str(message.get("sender_role"))
    if sender_role.endswith("CUSTOMER"):   # tolerate enum or "SenderRole.CUSTOMER"
        recipient = _identity_channel("vendor", convo.vendor_id)
    else:
        recipient = _identity_channel("user", convo.customer_user_id)

    frame = {
        "type": "MESSAGE",
        "conversation_id": str(conversation_id),
        "message": _jsonable(message),
    }
    redis = await _get_redis()
    await redis.publish(recipient, json.dumps(frame))


async def publish_read(conversation_id: UUID, reader_role: str,
                       vendor_id: UUID, customer_user_id: UUID, read_up_to) -> None:
    """Tell the OTHER side that their messages were read."""
    if reader_role.upper().endswith("CUSTOMER"):
        recipient = _identity_channel("vendor", vendor_id)
    else:
        recipient = _identity_channel("user", customer_user_id)
    frame = {
        "type": "READ",
        "conversation_id": str(conversation_id),
        "reader_role": reader_role,
        "read_up_to": read_up_to.isoformat() if hasattr(read_up_to, "isoformat") else str(read_up_to),
    }
    redis = await _get_redis()
    await redis.publish(recipient, json.dumps(frame))


def _jsonable(message: dict) -> dict:
    """Stringify UUIDs/datetimes in a MessageOut dict for JSON transport."""
    out = {}
    for k, v in message.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, UUID):
            out[k] = str(v)
        elif v is not None and v.__class__.__name__ in ("SenderRole", "MessageKind"):
            out[k] = v.value
        else:
            out[k] = v
    return out


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket, token: str = Query(...), role: str = Query("CUSTOMER")):
    """
    Live chat socket. Connect with: wss://HOST/PREFIX/ws/chat?token=JWT&role=CUSTOMER
    The client subscribes (by connecting) to its OWN identity channel; the server
    pushes MESSAGE / READ frames as they arrive via Redis.

    Outbound (server->client): JSON WsFrame ({type, conversation_id, message, ...}).
    Inbound (client->server): we accept PING (-> PONG) and TYPING (relayed); the
    actual SEND goes through the REST endpoint (persist-then-push), so the socket
    is receive-primary.
    """
    # ── Authenticate (ASSUMPTION: adjust to your JWT verifier) ────────────────
    identity = await _authenticate(token, role)
    if identity is None:
        await websocket.close(code=1008)  # policy violation
        return

    identity_key = identity  # "user:{uuid}" or "vendor:{uuid}"
    await manager.connect(identity_key, websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            await _handle_inbound(websocket, identity_key, raw)
    except WebSocketDisconnect:
        await manager.disconnect(identity_key, websocket)
    except Exception:
        await manager.disconnect(identity_key, websocket)
        try:
            await websocket.close()
        except Exception:
            pass


async def _handle_inbound(ws: WebSocket, identity_key: str, raw: str) -> None:
    try:
        frame = json.loads(raw)
    except Exception:
        return
    t = (frame.get("type") or "").upper()
    if t == "PING":
        await ws.send_text(json.dumps({"type": "PONG"}))
    elif t == "TYPING":
        # Relay a typing indicator to the other side, if provided.
        convo_id = frame.get("conversation_id")
        if convo_id:
            await _relay_typing(identity_key, convo_id, frame.get("typing_role"))
    # SEND is intentionally not handled here — clients POST to the REST endpoint
    # so the message is persisted first, then pushed back over the socket.


async def _relay_typing(sender_identity: str, conversation_id: str, typing_role) -> None:
    from app.models.chat_model import Conversation
    db = SessionLocal()
    try:
        convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if convo is None:
            return
        # recipient = the other side relative to the typer's identity
        if sender_identity.startswith("user:"):
            recipient = _identity_channel("vendor", convo.vendor_id)
        else:
            recipient = _identity_channel("user", convo.customer_user_id)
        frame = {"type": "TYPING", "conversation_id": str(conversation_id), "typing_role": typing_role}
        redis = await _get_redis()
        await redis.publish(recipient, json.dumps(frame))
    finally:
        db.close()


# ── Auth helper ───────────────────────────────────────────────────────────────

async def _authenticate(token: str, role: str) -> Optional[str]:
    """
    Validate the JWT (same secret/alg as account_module) and return the caller's
    identity_key:
        "user:{user_uuid}"   for a CUSTOMER
        "vendor:{vendor_uuid}" for a VENDOR

    Matches account_module.get_current_user: the token claim `sub` is the EMAIL;
    we look the User up by email, then resolve their UUID. For role=VENDOR we map
    to their vendor via Vendor.user_id (same as /Account/user/exists).
    """
    try:
        from jose import jwt, JWTError
        from app.config.settings import get_settings
        settings = get_settings()
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        except JWTError:
            return None
        email = payload.get("sub")
        if not email:
            return None
    except Exception:
        return None

    db = SessionLocal()
    try:
        from app.models.account_model import User
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            return None

        r = (role or "CUSTOMER").upper()
        if r == "VENDOR":
            from app.models.vendor_model import Vendor
            v = db.query(Vendor).filter(Vendor.user_id == user.id).first()
            if v is None:
                return None
            return f"vendor:{v.vendor_id}"
        return f"user:{user.id}"
    finally:
        db.close()