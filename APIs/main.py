from fastapi import FastAPI
from app.routers import apis_test_router, vendor_router,account_router, customer_router, service_router, booking_router
from app.config.db.postgresql import Base, engine
from sqlalchemy.orm import Session
from app.models.api_test_model import Test
from app.models.account_model import User
from app.models.vendor_model import Vendor
from app.models.customer_model import customer
from app.models.service_model import Add_Service
from app.models.booking_model import Booking
from app.config.db.postgresql import SessionLocal, engine

# flush the db on every run 
Base.metadata.drop_all(bind=engine)


#re-create the db
Base.metadata.create_all(bind=engine)



app = FastAPI()


app.include_router(apis_test_router.router)
app.include_router(account_router.router)
app.include_router (vendor_router.router)
app.include_router (customer_router.router)
app.include_router(service_router.router)
app.include_router(booking_router.router)