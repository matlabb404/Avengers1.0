
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
from datetime import timedelta



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


def get_secure_string_vendor():
    with open('cached_keys.txt', 'r') as file:
        lines = file.readlines()
    for line in lines:
        if "vendor" in line:
            return line.strip()  # Return the line without leading/trailing whitespace
    return None

def get_secure_string_service():
    try:
        with open('cached_keys.txt', 'r') as file:
            lines = file.readlines()
        for line in lines:
            if "service" in line:
                return line.strip() 
    except FileNotFoundError:
        return None
    return None

'''
def save_secure_string_service(text):
    with open('cached_keys.txt', 'r') as file:
        lines = file.readlines()
    with open('cached_keys.txt', 'w') as file:
        file.write('')
        for line in lines:
            if "service" in line:
                file.write(text+'\n')
            else:
                file.write(line)
    return get_secure_string_service()

# Hash the key using hashlib for a more efficient cache key

cache_key = get_secure_string_service()
'''
def save_secure_string_service(text):
    try:
        with open('cached_keys.txt', 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        lines = []

    with open('cached_keys.txt', 'w') as file:
        file.write('')
        for line in lines:
            if "service" in line:
                file.write(text + '\n')
            else:
                file.write(line)
        if not any("service" in line for line in lines):
            file.write(text + '\n')
    return get_secure_string_service()

# Hash the key using hashlib for a more efficient cache key
cache_key = get_secure_string_service()
if not cache_key:
    cache_key = generate_secure_string()
    save_secure_string_service(cache_key)


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
    save_secure_string_service(f"service:{hashlib.md5(generate_secure_string().encode()).hexdigest()}")
    vendor_id = redis_client.get(get_secure_string_vendor()).decode('utf-8')
    #if vendor_id:
    #   vendor_id = vendor_id.decode('utf-8')
    #else:
        # Generate a new vendor ID using UUID (or fetch it from your database)
    #    vendor_id = str(uuid.uuid4())
        
        # Store the vendor_id in Redis with an expiration time of 24 hours
    #    redis_client.setex(cache_key, timedelta(hours=24), vendor_id)

    # Use the vendor ID to add the big service
    response = big_service_mdl.add_service(db, big_service=big_service, add_vendor_id=str(vendor_id))
    response_with_vendor_id = {"vendor_id": vendor_id, "response": response}
    return response_with_vendor_id

@router.get("/get_service/{service_id}", tags=["Big Service"])
async def get_service(service_id: str, db: Session = Depends(get_db)):
    cached_service_id = redis_client.get(get_secure_string_vendor())
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
    
@router.get("/get_all_service_by_vendor/{vendor_id}", tags=["Big Service"])
async def get_all_service_by_vendor(vendor_id: str, db:Session= Depends(get_db)):
    service = big_service_mdl.get_service_by_vendor(db=db, vendor_id=vendor_id)
    return service