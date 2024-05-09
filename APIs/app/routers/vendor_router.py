from fastapi import APIRouter, Depends
from uuid import UUID
from typing import Annotated
import app.modules.vendor_module as vendor_mdl
import app.models.account_model as acct_mdl
from app.schemas import vendor_Schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from app.schemas.vendor_Schema import Gender
from datetime import timedelta
import redis,hashlib,secrets,string

router = APIRouter(prefix="/Vendor")

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

@router.post("/Add_vendor", tags=["Vendor"])
async def add_vendor( vendor: vendor_Schema.VendorCreateBase, db:Session=Depends(get_db)):
    cache_key = save_secure_string(f"vendor:{hashlib.md5(generate_secure_string().encode()).hexdigest()}")
    cached_vendor_id = redis_client.get(cache_key)
    if cached_vendor_id:
        return str(cached_vendor_id)
    
    responce = vendor_mdl.add_vendor(db=db, vendor=vendor)

    redis_client.setex(cache_key, timedelta(hours=24), str(responce))

    return redis_client.get(cache_key)


@router.post("/Vendor_Details", tags=["Vendor"])
async def vendor_details( vendor_detials_request: vendor_Schema.VendorDetailsCreateBase, db:Session=Depends(get_db)):
    cached_vendor_id = redis_client.get(get_secure_string()).decode('utf-8')
    if cached_vendor_id:
        print("This was returned from cache as the id",str(cached_vendor_id))
    response = vendor_mdl.add_vendor_details(db=db, vendor_id=str(cached_vendor_id) ,vendor_details_request=vendor_detials_request)
    return response


@router.get("/vendorid", tags=["Vendor"])
async def id(name:str):
    responce = vendor_mdl.gett(name=name)
    return responce

@router.get("/get_all_vendors", tags=["Vendor"])
async def get_all_vendors():
    all_vendors = vendor_mdl.get_all_vendors()
    return all_vendors

@router.get("/get_gender_vendors", tags=["Vendor"])
async def get_gender_vendors(gender:Gender):
    gender_vendors = vendor_mdl.get_gender_vendors(gender)
    return gender_vendors