from app.realtime import chat_ws
from fastapi import FastAPI
from app.routers import (apis_test_router, media_router, notification_router, posts_router, vendor_router,
account_router, customer_router, service_router, booking_router, payment_router,
following_router, likes_router, discover_router, comments_router, explore_router, search_router,
chat_router)
from app.config.db.postgresql import Base, engine
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
# import app.handlers.notification_handlers  # noqa: F401 — side-effect import
import app.events.notification_events  # registers booking notification handlers
import app.models.notification_model   # notifications / preferences / vendor_mutes tables
import app.models.device_token_model   # device_tokens table

# flush the db on every run 
# Base.metadata.drop_all(bind=engine)

#re-create the db
with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
Base.metadata.create_all(bind=engine)

app = FastAPI(root_path="/secret/test/avengers/test/backend/dev")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins; adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(apis_test_router.router)
app.include_router(account_router.router)
app.include_router (vendor_router.router)
app.include_router (customer_router.router)
app.include_router(service_router.router)
app.include_router(posts_router.router)
app.include_router(media_router.router)
app.include_router(likes_router.router)
app.include_router(comments_router.router)
app.include_router(booking_router.router)
app.include_router(payment_router.router)
app.include_router(following_router.router)
app.include_router(discover_router.router)
app.include_router(explore_router.router)
app.include_router(search_router.router)
app.include_router(chat_router.router)
app.include_router(chat_ws.router)
app.include_router(notification_router.router)

@app.on_event("startup")
async def _start_chat_pubsub():
    await chat_ws.start_pubsub()

@app.on_event("shutdown")
async def _stop_chat_pubsub():
    await chat_ws.stop_pubsub()