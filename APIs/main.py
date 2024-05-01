from fastapi import FastAPI
from app.routers import apis_test_router
from app.config.db.postgresql import Base, engine
from sqlalchemy.orm import Session
from app.models.api_test_model import Test 
from app.config.db.postgresql import SessionLocal, engine

# flush the db on every run 
Base.metadata.drop_all(bind=engine)


#re-create the db
Base.metadata.create_all(bind=engine)



app = FastAPI()


app.include_router(apis_test_router.router)