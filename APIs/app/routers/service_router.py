
from app.models.account_model import User
from app.modules.account_module import get_current_user
from app.modules.vendor_module import get_current_vendor
from app.services.storage import save_file
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
from typing import List, Optional
import json
from typing import Annotated
import app.modules.big_services_module as big_service_mdl
from app.schemas import big_services_schema
from app.modules.service_module import add_s, get_all_services, get_allprice_history, add_price_history, get_price_history, update_price_history
import app.models.service_model as service_mdl
from app.schemas import services_schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
import hashlib,secrets,string
from datetime import timedelta



router = APIRouter(prefix="/Service")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/Add_service", tags=["Service"])
async def add_service(old_service: services_schema.ServicesDropDownOption, new_service: str, db:Session=Depends(get_db)):
    service = old_service
    if new_service != "None":
        service = new_service
    lowercase = service.lower()
    nospace = lowercase.replace(" ","")
    strid = nospace
    responce = add_s(db=db, strid= strid,service=service)
    return responce

@router.get("/get_all_services", tags=["Service"])
async def get_all_small_services(db:Session=Depends(get_db)):
    return get_all_services(db=db)

# Big Service CRUD operations
@router.post("/Add_big_service", tags=["Big Service"])
async def add_big_service(
    # We receive the metadata as a JSON string or individual Form fields
    price: Optional[float] = Form(...),
    price_history: str = Form(None),
    add_service_id: str = Form(...),
    description: Optional[str] = Form(None),
    # We receive the list of images as actual Files
    images: List[UploadFile] = File(None), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    vendor = get_current_vendor(current_user.id, db=db)
    image_urls = []

    if images is not None:
        # Now 'images' is a real list of file objects we can iterate over
        for file in images:
            if file.filename:
                # This calls your save_file (VPS or S3 logic)
                path_suffix = f"vendor_{vendor.vendor_id}/services"
                image_url = save_file(file, folder_path=path_suffix)
                image_urls.append(image_url)

    new_service = service_mdl.Service(
        add_vendor_id=vendor.vendor_id,
        price=price,
        price_history=price_history,
        add_service_id=add_service_id,
        image_url=image_urls,
        description=description
    )
    response = big_service_mdl.add_service(db, big_service=new_service, add_vendor_id=vendor.vendor_id)
    response_with_vendor_id = {"vendor_id": vendor.vendor_id, "response": response}
    return response_with_vendor_id

@router.get("/get_service", tags=["Big Service"])
async def get_service(service_id: str, db: Session = Depends(get_db), current_user : User = Depends(get_current_user)):
    db_service = big_service_mdl.get_service(db=db, service_id=service_id)
    if db_service is None:
        return "Not Found"
    return db_service

@router.put("/update_service", tags=["Big Service"])
async def update_service(
    service_id: str,
    add_vendor_id: str = Form(...), 
    price: Optional[float] = Form(...),
    price_history: Optional[str] = Form(...),
    add_service_id: str = Form(...),
    description: Optional[str] = Form(None),
    # Optional: Make images optional so they don't HAVE to upload new ones to change the price
    images: Optional[List[UploadFile]] = File(None), 
    db: Session = Depends(get_db)
):
    # 1. Fetch the existing record
    existing_service = big_service_mdl.get_service(db=db, service_id=service_id)
    if not existing_service:
        raise HTTPException(status_code=404, detail="Service not found")

    # 2. Update basic fields directly#
    existing_service.price_history = price_history  # Keep old price history unless explicitly changed
    existing_service.price = price
    existing_service.add_service_id = add_service_id
    existing_service.description = description
    existing_service.add_vendor_id = add_vendor_id

    # 3. Handle Images (The "City" Way - only update if new ones are sent)
    if images and len(images) > 0:
        # Check if the first file actually has a filename (FastAPI quirk)
        if images[0].filename != "":
            new_image_urls = []
            for file in images:
                path_suffix = f"vendor_{add_vendor_id}/services"
                image_url = save_file(file, folder_path=path_suffix)
                new_image_urls.append(image_url)
            
            # NOTE: This replaces the old list. 
            # If you want to APPEND, use: existing_service.image_url.extend(new_image_urls)
            existing_service.image_url = new_image_urls

    # 4. Commit changes
    try:
        db.commit()
        db.refresh(existing_service)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return existing_service

'''

@router.delete("/delete_service/{service_id}", tags=["Big Service"])
async def delete_service(service_id: str, db: Session = Depends(get_db)):
    db_service = big_service_mdl.get_service(db=db, service_id=service_id)
    if db_service is None:
        return "Not Found"
    return big_service_mdl.delete_service(db=db, service=db_service)
'''

@router.delete("/delete_service", tags=["Big Service"])
async def delete_service(service_id: str, db: Session = Depends(get_db)):
    deleted = big_service_mdl.delete_service(db=db, service_id=service_id)
    if deleted:
        return {"message": "Service deleted successfully"}
    else:
        return {"message": "Service not found"}
    
@router.get("/get_all_service_by_vendor", tags=["Big Service"])
async def get_all_service_by_vendor(db:Session= Depends(get_db), current_user : User = Depends(get_current_user) ):
    vendor = get_current_vendor(current_user.id, db=db)
    service = big_service_mdl.get_service_by_vendor(db=db, vendor_id=vendor.vendor_id)
    return service

@router.get("/get_allfull_service", tags=["Big Service"])
async def get_all_full_service(db:Session= Depends(get_db), current_user : User = Depends(get_current_user) ):
    vendor = get_current_vendor(current_user.id, db=db)
    service = big_service_mdl.get_all_service(db=db)
    return service

@router.post("/add_price_history", tags=["Price History"])
async def add_price(service_id:str, price:float, db:Session=Depends(get_db), current_user: User = Depends(get_current_user)):
    vendor = get_current_vendor(current_user.id, db=db)
    new_price_history = add_price_history(db=db, service_id=service_id, add_vendor_id=str(vendor.vendor_id), price=price)
    return new_price_history

@router.get("/get_price_history", tags=["Price History"])
async def get_single_price(service_id:str, db:Session=Depends(get_db), current_user: User = Depends(get_current_user)):
    vendor = get_current_vendor(current_user.id, db=db)
    price_histor = get_price_history(db=db, service_id=service_id, add_vendor_id=str(vendor.vendor_id))
    if price_histor is None:
        return "Not Found"
    return price_histor

@router.get("/get_all_price_history", tags=["Price History"])
async def get_all_price(db:Session=Depends(get_db), current_user: User = Depends(get_current_user)):
    vendor = get_current_vendor(current_user.id, db=db)
    price_histor = get_allprice_history(db=db, vendor_id=str(vendor.vendor_id))
    if price_histor is None:
        return "Not Found"
    return price_histor

@router.put("/update_price_history", tags=["Price History"])
async def update_price(service_id:str, price:float, db:Session=Depends(get_db)):
    new_price_history = update_price_history(db=db, service_id=service_id, new_price=price)
    return new_price_history