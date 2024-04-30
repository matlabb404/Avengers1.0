from fastapi import APIRouter
import app.modules.apis_test_modules as api_test_module


router = APIRouter(prefix="/test")


#router gets data from modules

@router.get("/")
async def print_name(name:str):
    responce = api_test_module.print_name(name)
    return responce