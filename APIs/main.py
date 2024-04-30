from fastapi import FastAPI
from app.routers import apis_test_router

app = FastAPI()


app.include_router(apis_test_router.router)