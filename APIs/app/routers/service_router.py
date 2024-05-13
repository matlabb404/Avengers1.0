from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
import app.modules.big_services_module as big_service_mdl
from app.schemas import big_services_schema
from app.modules.service_module import add_s
import app.models.service_model as service_mdl
from app.schemas import services_schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
import redis,hashlib,secrets,string



router = APIRouter(prefix="/Service")

# Initialize Redis client
redis_client = redis.Redis(host='localhost', port=6379,db=0)
# Send a ping request and check the response 
print("Response:", redis_client.ping())


#generate key
def generate_secure_string(length=16):
    letters = string.ascii_letters
    random_string = ''.join(secrets.choice(letters) for _ in range(length))
    return random_string


def get_secure_string():
    return open('cached_keys.txt', 'r').readlines()[-1].strip()


def save_secure_string(text):
    open('cached_keys.txt', 'w').write('')
    open('cached_keys.txt', 'a').write(text+'\n')
    return get_secure_string()

# Hash the key using hashlib for a more efficient cache key

cache_key = get_secure_string()



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/Add_service", tags=["Service"])
async def add_service(service: services_schema.ServicesDropDownOption, db:Session=Depends(get_db)):
    responce = add_s(db=db, service=service)
    return responce



@router.post("/Add_big_service", tags=["Big Service"])
async def add_big_service(big_service: big_services_schema.ServiceSchema, db: Session = Depends(get_db)):
    response= big_service_mdl.add_service(db, big_service=big_service)
    return response



@router.get("/get_service/{service_id}", tags=["Big Service"])
async def get_service(service_id: str, db: Session = Depends(get_db)):
    cached_service_id = redis_client.get(get_secure_string())
    if cached_service_id is not None:
        cached_service_id = cached_service_id.decode('utf-8')
    db_service = big_service_mdl.get_service(db=db, service_id=service_id)
    if db_service is None:
        return "Not Found"
    return db_service



@router.put("/update_service/{service_id}", tags=["Big Service"])
async def update_service(service_id: str, service_update: big_services_schema.ServiceUpdate, db: Session = Depends(get_db)):
    # Retrieve existing service data
    existing_service = big_service_mdl.get_service(db=db, service_id=service_id)
    if existing_service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    # Update service details
    for field, value in service_update.dict().items():
        setattr(existing_service, field, value)
    
    db.commit()
    db.refresh(existing_service)
    return existing_service

'''

@router.delete("/delete_service/{service_id}", tags=["Big Service"])
async def delete_service(service_id: str, db: Session = Depends(get_db)):
    db_service = big_service_mdl.get_service(db=db, service_id=service_id)
    if db_service is None:
        return "Not Found"
    return big_service_mdl.delete_service(db=db, service=db_service)
'''
@router.delete("/delete_service/{service_id}", tags=["Big Service"])
async def delete_service(service_id: str, db: Session = Depends(get_db)):
    deleted = big_service_mdl.delete_service(db=db, service_id=service_id)
    if deleted:
        return {"message": "Service deleted successfully"}
    else:
        return {"message": "Service not found"}
