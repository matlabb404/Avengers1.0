from fastapi import APIRouter, Depends, HTTPException
from app.modules import customer_modules
from app.models import customer_model
from app.schemas import customer_schema
from app.modules.account_module import get_current_user
from app.models.customer_model import customer
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from datetime import datetime,timedelta
from app.models.account_model import User
from typing import Any, Dict
import redis,hashlib,secrets,string


router = APIRouter(prefix="/customer")

redis_client = redis.Redis(host='localhost', port=6379,db=0)
# Send a ping request and check the response 
print("Response:", redis_client.ping())


#generate key
def generate_secure_string(length=16):
    letters = string.ascii_letters
    random_string = ''.join(secrets.choice(letters) for _ in range(length))
    return random_string


def get_secure_string_customer():
    with open('cached_keys.txt', 'r') as file:
        lines = file.readlines()
    for line in lines:
        if "customer" in line:
            return line.strip()  # Return the line without leading/trailing whitespace
    return None

def save_secure_string_customer(text):
    try:
        with open('cached_keys.txt', 'r') as file:
            lines = file.readlines()
    except FileNotFoundError:
        lines = []

    with open('cached_keys.txt', 'w') as file:
        file.write('')
        for line in lines:
            if "customer" in line:
                file.write(text + '\n')
            else:
                file.write(line)
        if not any("customer" in line for line in lines):
            file.write(text + '\n')
    return get_secure_string_customer()



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/Add_customer", tags=["customer"])
async def add_customer(customer: customer_schema.CustomerCreateBase, db:Session=Depends(get_db),  current_user : User= Depends(get_current_user)):
    user_ida = current_user.id
    customer.last_edited = datetime.now() # Add today's date to the 'last_edited' field
    save_secure_string_customer(f"customer:{hashlib.md5(generate_secure_string().encode()).hexdigest()}")
    if redis_client.get(get_secure_string_customer()):
        print(str(redis_client.get(get_secure_string_customer())))
    response = customer_modules.add_customer(db=db, customer=customer, user_id_=use)
    redis_client.setex(get_secure_string_customer(), timedelta(hours=24), str(response.customer_id))
    return response


@router.put("/update_customer/{customer_id}", tags=["customer"])
async def update_customer(customer_id: int, update_data: customer_schema.CustomerUpdate, db: Session = Depends(get_db)):
    # Retrieve existing customer data
    existing_customer = db.query(customer).filter(customer.customer_id == customer_id).first()
    if existing_customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")  
    # Update customer details
    for field, value in update_data.dict().items():
        setattr(existing_customer, field, value)
    
    db.commit()
    db.refresh(existing_customer)
    return existing_customer


@router.delete("/delete_customer/{customer_id}", tags=["customer"])
async def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    deleted = customer_modules.delete_customer_by_id(db, customer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted successfully"}