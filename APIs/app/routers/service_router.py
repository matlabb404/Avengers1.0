
import shutil

from app.models.account_model import User
from app.modules.account_module import get_current_user
from app.modules.vendor_module import get_current_vendor
from app.services.storage import save_file, process_video_upload, UPLOAD_STATUS
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile, Query, Request, Header, BackgroundTasks
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
import uuid
import os

UPLOAD_DIR = "uploads/tmp"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

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
    images: Optional[List[str]] = Form(None), 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    vendor = get_current_vendor(current_user.id, db=db)

    new_service = service_mdl.Service(
        add_vendor_id=vendor.vendor_id,
        price=price,
        price_history=price_history,
        add_service_id=add_service_id,
        image_url=images,
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
    images: Optional[List[str]] = Form(None), 
    db: Session = Depends(get_db)
):
    # 1. Fetch the existing record
    existing_service = big_service_mdl.get_service(db=db, service_id=service_id)
    if not existing_service:
        raise HTTPException(status_code=404, detail="Service not found")

    # 2. Update basic fields directly#
    existing_service.price_history = price_history  # Keep old price history unless explicitly changed
    existing_service.price = price if price is not None else existing_service.price  # Only update if new price provided
    existing_service.add_service_id = add_service_id
    existing_service.description = description if description is not None else existing_service.description  # Only update if new description provided
    existing_service.add_vendor_id = add_vendor_id
    existing_service.image_url = images if images is not None else existing_service.image_url  # Only update if new images provided

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
async def get_all_service_by_vendor(db:Session= Depends(get_db), page: int = Query(default=0, ge=0), page_size: int = Query(default=20, ge=1, le=100), current_user : User = Depends(get_current_user) ):
    vendor = get_current_vendor(current_user.id, db=db)
    service = big_service_mdl.get_service_by_vendor(db=db, vendor_id=vendor.vendor_id)
    return service

@router.get("/get_allfull_service", tags=["Big Service"])
async def get_all_full_service(db:Session= Depends(get_db), page: int = Query(default=0, ge=0), page_size: int = Query(default=20, ge=1, le=100), current_user : User = Depends(get_current_user) ):
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

# Uploads section
@router.post("/upload/init", tags=["Big Service"])
async def init_upload(current_user: User = Depends(get_current_user)):
    upload_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, upload_id)

    # create empty file
    os.makedirs(file_path, exist_ok=True)

    return {"uploadId": upload_id}

@router.post("/upload/chunk", tags=["Big Service"])
async def upload_chunk(
    request: Request,
    upload_id: str = Header(...),
    chunk_index: int = Header(...),
    current_user: User = Depends(get_current_user)
):
    chunk_dir = os.path.join(UPLOAD_DIR, upload_id)
    os.makedirs(chunk_dir, exist_ok=True)

    chunk = await request.body()

    chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index}.part")

    with open(chunk_path, "wb") as f:
        f.write(chunk)

    return {"status": "chunk received", "index": chunk_index}

@router.post("/upload/complete", tags=["Big Service"])
async def complete_upload(
    data: dict,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    upload_id = data.get("uploadId")
    chunk_dir = os.path.join(UPLOAD_DIR, upload_id)
    files = os.listdir(chunk_dir)

    if len(files) == 0:
        raise HTTPException(400, "No chunks uploaded")
    if not os.path.exists(chunk_dir):
        raise HTTPException(status_code=404, detail="Upload not found")
    
    merged_path = os.path.join(UPLOAD_DIR, f"{upload_id}.mp4")  # Assuming mp4, can be dynamic based on metadata 

    # Merge chunks in correct order
    with open(merged_path, "wb") as output_file:
        for chunk_file in sorted(os.listdir(chunk_dir), key=lambda x: int(x.split("_")[1].split(".")[0])):
            chunk_path = os.path.join(chunk_dir, chunk_file)
            with open(chunk_path, "rb") as input_file:
                shutil.copyfileobj(input_file, output_file)

    #cleanuo chunks
    shutil.rmtree(chunk_dir)

    # mark as queued
    UPLOAD_STATUS[upload_id] = {"status": "queued"}

    # ✅ run in background
    background_tasks.add_task(process_video_upload, upload_id, merged_path)

    return {
        "uploadId": upload_id,
        "status": "processing"
    }

@router.get("/upload/status/{upload_id}", tags=["Big Service"])
async def get_upload_status(upload_id: str):
    status = UPLOAD_STATUS.get(upload_id)

    if not status:
        raise HTTPException(status_code=404, detail="Upload not found")

    return status