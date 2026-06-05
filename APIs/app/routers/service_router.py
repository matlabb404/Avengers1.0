
import shutil

from app.models.account_model import User
from app.modules.account_module import get_current_user
from app.modules.vendor_module import get_current_vendor
from app.schemas.services_schema import SetServicePriceRequest
from app.services.storage import save_file, process_video_upload, UPLOAD_STATUS
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile, Query, Request, Header, BackgroundTasks
from typing import List, Optional
import json
from typing import Annotated
import app.modules.big_services_module as big_service_mdl
from app.schemas.big_services_schema import ServiceUpdate, ServiceInfo, VendorInfo, AddServiceInfo, PriceHistoryInfo, FullServiceResponse
from app.modules.service_module import add_booking_price, add_s, update_s, delete_s, get_all_services, get_allprice_history, add_price_history, get_price_history, update_price_history
import app.models.service_model as service_mdl
from app.schemas import services_schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from datetime import timedelta
from uuid import UUID
import os
from pydantic import BaseModel, Field

UPLOAD_DIR = "uploads/tmp"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

router = APIRouter(prefix="/services", tags=["services"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/")
def Add_big_service(
    price: Optional[float] = Form(None),
    price_history: Optional[UUID] = Form(None),
    add_service_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    # Ordered media asset ids, sent as repeated form fields: asset_ids=<uuid>&asset_ids=<uuid>
    asset_ids: Optional[List[UUID]] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    vendor = db.query(Vendor).filter(Vendor.user_id == current_user.id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor profile not found")
 
    payload = ServiceUpdate(
        price=price,
        price_history=price_history,
        add_service_id=add_service_id,
        description=description,
        asset_ids=asset_ids,
    )
 
    response = big_service_mdl.add_service(
        db,
        owner_id=current_user.id,
        big_service=payload,
        add_vendor_id=vendor.vendor_id,
    )
    return {"vendor_id": vendor.vendor_id, "response": response}
 
 
@router.get("/{service_id}", response_model=FullServiceResponse)
def get_service(service_id: str, db: Session = Depends(get_db)):
    return big_service_mdl.get_service(db, service_id)
 
 
@router.get("/vendor/{vendor_id}", response_model=List[FullServiceResponse])
def get_service_by_vendor(vendor_id: str, db: Session = Depends(get_db)):
    return big_service_mdl.get_service_by_vendor(db, vendor_id)
 
 
@router.get("/", response_model=List[FullServiceResponse])
def get_all_service(db: Session = Depends(get_db)):
    return big_service_mdl.get_all_service(db)
 
 
@router.put("/{service_id}", response_model=FullServiceResponse)
def update_service(
    service_id: str,
    price: Optional[float] = Form(None),
    price_history: Optional[UUID] = Form(None),
    add_service_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    asset_ids: Optional[List[UUID]] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payload = ServiceUpdate(
        price=price,
        price_history=price_history,
        add_service_id=add_service_id,
        description=description,
        asset_ids=asset_ids,
    )
    # NOTE: pre-existing gap — this does not yet verify the vendor owns this
    # service. owner_id only gates asset ownership. Add a service-ownership
    # check here when you harden the endpoint.
    updated = big_service_mdl.update_service(
        db, service_id, payload, owner_id=current_user.id
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Service not found")
    return updated
 
 
@router.delete("/{service_id}")
def delete_service(service_id: str, db: Session = Depends(get_db)):
    if not big_service_mdl.delete_service(db, service_id):
        raise HTTPException(status_code=404, detail="Service not found")
    return {"detail": "Service deleted"}

# ------------------------Price Hoistory
@router.post("/add_price_history", tags=["Price History"])
async def add_price(service_id:str, price:float, request: SetServicePriceRequest, db:Session=Depends(get_db), current_user: User = Depends(get_current_user)):
    """Vendor sets the full and Bookingprice for one of their service offerings."""
    vendor = get_current_vendor(current_user.id, db=db)
    new_price_history = add_price_history(db=db, service_id=service_id, request=request, add_vendor_id=str(vendor.vendor_id), price=price)
    return new_price_history

@router.patch("/{service_id}/booking_price", tags=["services"])
async def set_service_price(service_id: str, request: SetServicePriceRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Vendor sets/updates the price for one of their service offerings."""
    vendor = get_current_vendor(current_user.id, db=db)
    return add_booking_price(db=db, service_id=service_id, request=request, vendor_id=vendor.vendor_id)

@router.get("/get_price_history", tags=["Price History"])
async def get_single_price(service_id:str, db:Session=Depends(get_db), current_user: User = Depends(get_current_user)):
    vendor = get_current_vendor(current_user.id, db=db)
    price_histor = get_price_history(db=db, service_id=service_id, add_vendor_id=vendor.vendor_id)
    if price_histor is None:
        return "Not Found"
    return price_histor

@router.get("/get_all_price_history", tags=["Price History"])
async def get_all_price(db:Session=Depends(get_db), current_user: User = Depends(get_current_user)):
    vendor = get_current_vendor(current_user.id, db=db)
    price_histor = get_allprice_history(db=db, vendor_id=vendor.vendor_id)
    if price_histor is None:
        return "Not Found"
    return price_histor

@router.put("/update_price_history", tags=["Price History"])
async def update_price(service_id:str, price:float, db:Session=Depends(get_db)):
    new_price_history = update_price_history(db=db, service_id=service_id, new_price=price)
    return new_price_history


# =--------------------------=-------------DEPRECATED UPLOAD ENDPOINTS (moved to media_router)---------------------------- 
# ----------------------------------------Uploads section
# @router.post("/upload/init", tags=["Big Service"])
# async def init_upload(current_user: User = Depends(get_current_user)):
#     upload_id = str(uuid.uuid4())
#     file_path = os.path.join(UPLOAD_DIR, upload_id)

#     # create empty file
#     os.makedirs(file_path, exist_ok=True)

#     return {"uploadId": upload_id}

# @router.post("/upload/chunk", tags=["Big Service"])
# async def upload_chunk(
#     request: Request,
#     upload_id: str = Header(...),
#     chunk_index: int = Header(...),
#     current_user: User = Depends(get_current_user)
# ):
#     chunk_dir = os.path.join(UPLOAD_DIR, upload_id)
#     os.makedirs(chunk_dir, exist_ok=True)

#     chunk = await request.body()

#     chunk_path = os.path.join(chunk_dir, f"chunk_{chunk_index}.part")

#     with open(chunk_path, "wb") as f:
#         f.write(chunk)

#     return {"status": "chunk received", "index": chunk_index}

# @router.post("/upload/complete", tags=["Big Service"])
# async def complete_upload(
#     data: dict,
#     background_tasks: BackgroundTasks,
#     current_user: User = Depends(get_current_user)
# ):
#     upload_id = data.get("uploadId")
#     chunk_dir = os.path.join(UPLOAD_DIR, upload_id)
#     files = sorted(os.listdir(chunk_dir),key=lambda x: int(x.split("_")[1].split(".")[0]))

#     if len(files) == 0:
#         raise HTTPException(400, "No chunks uploaded")
#     if not os.path.exists(chunk_dir):
#         raise HTTPException(status_code=404, detail="Upload not found")
    
#     merged_path = os.path.join(UPLOAD_DIR, f"{upload_id}.mp4")  # Assuming mp4, can be dynamic based on metadata 

#     # Merge chunks in correct order
#     with open(merged_path, "wb") as output_file:
#         for chunk_file in files:
#             chunk_path = os.path.join(chunk_dir, chunk_file)
#             with open(chunk_path, "rb") as input_file:
#                 shutil.copyfileobj(input_file, output_file)

#     #cleanuo chunks
#     shutil.rmtree(chunk_dir)

#     # mark as queued
#     UPLOAD_STATUS[upload_id] = {"status": "queued"}

#     # ✅ run in background
#     background_tasks.add_task(process_video_upload, upload_id, merged_path)

#     return {
#         "uploadId": upload_id,
#         "status": "processing"
#     }

# @router.get("/upload/status/{upload_id}", tags=["Big Service"])
# async def get_upload_status(upload_id: str):
#     status = UPLOAD_STATUS.get(upload_id)

#     if not status:
#         raise HTTPException(status_code=404, detail="Upload not found")

#     return status