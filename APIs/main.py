from fastapi import FastAPI
from app.routers import apis_test_router, media_router, vendor_router,account_router, customer_router, service_router, booking_router, payment_router
from app.config.db.postgresql import Base, engine
from fastapi.middleware.cors import CORSMiddleware
import app.handlers.notification_handlers  # noqa: F401 — side-effect import

# flush the db on every run 
# Base.metadata.drop_all(bind=engine)

#re-create the db
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
app.include_router(media_router.router)
app.include_router(booking_router.router)
app.include_router(payment_router.router)