from fastapi import APIRouter, Depends
from uuid import UUID
from typing import Annotated
import app.modules.vendor_module as vendor_mdl
import app.models.account_model as acct_mdl
import app.modules.account_module as acct_module
from app.schemas import vendor_Schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from app.schemas.vendor_Schema import Gender
from datetime import timedelta
import redis ,hashlib,secrets,string

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

def get_secure_string_vendor():
    with open('cached_keys.txt', 'r') as file:
        lines = file.readlines()
    for line in lines:
        if "vendor" in line:
            return line.strip()  # Return the line without leading/trailing whitespace
    return None

def save_secure_string_vendor(text):
    try:
        with open('cached_keys.txt', 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        lines = []

    with open('cached_keys.txt', 'w') as file:
        file.write('')
        for line in lines:
            if "vendor" in line:
                file.write(text + '\n')
            else:
                file.write(line)
        if not any("vendor" in line for line in lines):
            file.write(text + '\n')
    return get_secure_string_vendor()


# Hash the key using hashlib for a more efficient cache key

cache_key = get_secure_string_vendor()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/Add_vendor", tags=["Vendor"])
async def add_vendor( vendor: vendor_Schema.VendorCreateBase, db:Session=Depends(get_db), current_user : acct_mdl.User = Depends(acct_module.get_current_user)):
    email = current_user.email
    cache_key = save_secure_string_vendor(f"vendor:{hashlib.md5(generate_secure_string().encode()).hexdigest()}")
    cached_vendor_id = redis_client.get(cache_key)
    if cached_vendor_id:
        print(str(cached_vendor_id))
    
    responce = vendor_mdl.add_vendor(db=db, vendor=vendor, vendor_emaail = email)

    redis_client.setex(cache_key, timedelta(hours=24), str(responce))

    return redis_client.get(cache_key)


@router.post("/Vendor_Details/{vendor_id}", tags=["Vendor"])
async def vendor_details( vendor_detials_request: vendor_Schema.VendorDetailsCreateBase, db:Session=Depends(get_db), current_user : acct_mdl.User = Depends(acct_module.get_current_user)):
    cached_vendor_id = redis_client.get(get_secure_string_vendor()).decode('utf-8')
    if cached_vendor_id:
        print("This was returned from cache as the id",str(cached_vendor_id))
    response = vendor_mdl.add_vendor_details(db=db, vendor_id=str(cached_vendor_id) ,vendor_details_request=vendor_detials_request)
    return response

@router.put("/Update_Vendor/{vendor_id}", tags=["Vendor"])
async def update_vendor(vendor_update: vendor_Schema.VendorCreateBase, db:Session=Depends(get_db), current_user : acct_mdl.User = Depends(acct_module.get_current_user)):
    cached_vendor_id = redis_client.get(get_secure_string_vendor()).decode('utf-8')
    if cached_vendor_id:
        print("This was returned from cache as the id",str(cached_vendor_id))
    response = vendor_mdl.vendor_update(db=db, vendor_id=str(cached_vendor_id) ,vendor_update=vendor_update)
    return response

@router.delete("/Delete_Vendor/{vendor_id}", tags=["Vendor"])
async def delete_vendor(db:Session=Depends(get_db), current_user : acct_mdl.User = Depends(acct_module.get_current_user)):
    cached_vendor_id = redis_client.get(get_secure_string_vendor()).decode('utf-8')
    if cached_vendor_id:
        print("This was returned from cache as the id",str(cached_vendor_id))
    response = vendor_mdl.vendor_delete(db=db, vendor_id=str(cached_vendor_id))
    return response

@router.delete("/Delete_Vendor_details/{vendor_id}/{venor_details_id}", tags=["Vendor"])
async def delete_vendor(vendor_id_details: UUID , db:Session=Depends(get_db),current_user : acct_mdl.User = Depends(acct_module.get_current_user)):
    response = vendor_mdl.vendor_delete(db=db, vendor_id=vendor_id_details)
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


##### For scheduling
@router.post("/Scheduling/{vendor_id}", tags=["Vendor"])
async def vendor_details( schedulebase: vendor_Schema.Scheduling, db:Session=Depends(get_db), current_user : acct_mdl.User = Depends(acct_module.get_current_user)):
    cached_vendor_id = redis_client.get(get_secure_string_vendor()).decode('utf-8')
    if cached_vendor_id:
        print("This was returned from cache as the id",str(cached_vendor_id))
    response = vendor_mdl.add_vendor_details(db=db, schedule_vendor_id=str(cached_vendor_id) ,schedulebase=schedulebase)
    return response