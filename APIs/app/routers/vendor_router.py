from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import Optional
import app.modules.vendor_module as vendor_mdl
import app.modules.booking_module as booking_module
import app.models.account_model as acct_mdl
import app.modules.account_module as acct_module
from app.schemas import vendor_Schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from app.schemas.vendor_Schema import Gender
from app.models.account_model import User
from app.modules.account_module import get_current_user
from datetime import timedelta, date

router = APIRouter(prefix="/Vendor")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/Add_vendor", tags=["Vendor"])
async def add_vendor( vendor: vendor_Schema.VendorCreateBase, db:Session=Depends(get_db),  current_user : User = Depends(get_current_user)):
    email = current_user.email
    user_id = current_user.id
    responce = vendor_mdl.add_vendor(db=db, vendor=vendor, vendor_emaail = email, user_id_=user_id)
    return responce

@router.get("/get_vendor", tags=["Vendor"])
async def get_vendor(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    vendor_record = vendor_mdl.get_current_vendor(current_user.id, db=db)
    if not vendor_record:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor_record

@router.post("/Vendor_Details", tags=["Vendor"])
async def vendor_details( vendor_detials_request: vendor_Schema.VendorDetailsCreateBase, db:Session=Depends(get_db), current_user : User = Depends(get_current_user)):
    vendor = vendor_mdl.get_current_vendor( current_user.id, db=db)
    response = vendor_mdl.add_vendor_details(db=db, vendor_id = vendor.vendor_id ,vendor_details_request=vendor_detials_request)
    return response

@router.put("/Update_Vendor", tags=["Vendor"])
async def update_vendor(vendor_update: vendor_Schema.VendorCreateBase, db:Session=Depends(get_db), current_user : User = Depends(get_current_user)):
    vendor = vendor_mdl.get_current_vendor( current_user.id, db=db)
    response = vendor_mdl.vendor_update(db=db, vendor_id= vendor.vendor_id ,vendor_update=vendor_update)
    return response

@router.delete("/Delete_Vendor", tags=["Vendor"])
async def delete_vendor(db:Session=Depends(get_db),current_user : User = Depends(get_current_user)):
    vendor = vendor_mdl.get_current_vendor( current_user.id, db=db)
    response = vendor_mdl.vendor_delete(db=db, vendor_id=vendor.vendor_id)
    return response

@router.delete("/Delete_Vendor_details", tags=["Vendor"])
async def delete_vendor(vendor_id_details: UUID , db:Session=Depends(get_db),current_user : User = Depends(get_current_user)):
    response = vendor_mdl.vendor_delete(db=db, vendor_id=vendor_id_details)
    return response

@router.get("/get_all_vendors", tags=["Vendor"])
async def get_all_vendors():
    all_vendors = vendor_mdl.get_all_vendors()
    return all_vendors

@router.get("/get_gender_vendors", tags=["Vendor"])
async def get_gender_vendors(gender:Gender):
    gender_vendors = vendor_mdl.get_gender_vendors(gender)
    return gender_vendors


# ============ SCHEDULE ENDPOINTS ============

@router.post("/{vendor_id}/schedule", tags=["Scheduling"], response_model=vendor_Schema.ScheduleResponse)
async def create_or_update_schedule(
    schedule: vendor_Schema.ScheduleCreate,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    """
    Create or update schedule (UPSERT).
    Use service_id="all" for default schedule.
    Use specific UUID for service-specific schedule.
    """
    vendor = vendor_mdl.get_current_vendor( current_user.id, db=db)
    vendor_id = vendor.vendor_id
    return vendor_mdl.upsert_schedule(db, vendor_id, schedule)

@router.patch("/{vendor_id}/schedule/{service_id}", tags=["Scheduling"])
async def update_schedule(
    service_id: str,
    update: vendor_Schema.ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    """
    Partially update existing schedule
    """
    vendor = vendor_mdl.get_current_vendor( current_user.id, db=db)
    vendor_id = vendor.vendor_id
    return vendor_mdl.update_schedule(db, vendor_id, service_id, update)

@router.get("/{vendor_id}/schedule", tags=["Scheduling"])
async def get_schedules(
    vendor_id: str,
    service_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get schedule(s).
    If service_id provided: returns that specific schedule (or falls back to "all")
    If no service_id: returns all schedules for the vendor
    """
    if service_id:
        schedule = vendor_mdl.get_schedule_for_service(db, vendor_id, service_id)
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return schedule
    else:
        return vendor_mdl.get_all_schedules(db, vendor_id)

@router.delete("/{vendor_id}/schedule/{service_id}", tags=["Scheduling"])
async def delete_schedule(
    service_id: str,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    """
    Delete service-specific schedule (reverts to default "all" schedule)
    Cannot delete "all" schedule - update it instead
    """
    vendor = vendor_mdl.get_current_vendor( current_user.id, db=db)
    vendor_id = vendor.vendor_id
    return vendor_mdl.delete_schedule(db, vendor_id, service_id)

# ============ EXCEPTION ENDPOINTS ============

@router.post("/{vendor_id}/exceptions", tags=["Scheduling"], response_model=vendor_Schema.ExceptionResponse)
async def create_exception(
    exception: vendor_Schema.ExceptionCreate,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    """
    Create schedule exception
    """
    vendor = vendor_mdl.get_current_vendor( current_user.id, db=db)
    vendor_id = vendor.vendor_id
    return vendor_mdl.create_exception(db, vendor_id, exception)

@router.get("/{vendor_id}/exceptions", tags=["Scheduling"])
async def get_exceptions(
    vendor_id: str,
    start_date: date,
    end_date: date,
    service_id: str = "all",
    db: Session = Depends(get_db)
):
    """
    Get exceptions with hierarchy (service-specific overrides "all")
    """
    return vendor_mdl.get_exceptions_for_service(
        db, vendor_id, start_date, end_date, service_id
    )

@router.put("/exceptions/{exception_id}", tags=["Scheduling"])
async def update_exception(
    exception_id: str,
    update: vendor_Schema.ExceptionBase,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    """
    Update existing exception
    """
    return vendor_mdl.update_exception(db, exception_id, update)

@router.delete("/exceptions/{exception_id}", tags=["Scheduling"])
async def delete_exception(
    exception_id: str,
    db: Session = Depends(get_db),
    current_user : User = Depends(get_current_user)
):
    """
    Delete exception
    """
    return vendor_mdl.delete_exception(db, exception_id)

@router.post("/{vendor_id}/cleanup-exceptions", tags=["Scheduling"])
async def cleanup_old_exceptions(
    vendor_id: str,
    db: Session = Depends(get_db)
):
    """
    Manually trigger cleanup of past exceptions
    """
    return vendor_mdl.cleanup_past_exceptions(db, vendor_id)

# ============ AVAILABILITY ENDPOINT ============

@router.get("/{vendor_id}/availability", tags=["Scheduling"])
async def get_availability(
    vendor_id: str,
    service_id: str,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    """
    Get available slots considering:
    - Service-specific schedule OR default "all" schedule
    - Service-specific exceptions + "all" exceptions
    - Walk-in availability
    """
    if (end_date - start_date).days > 90:
        raise HTTPException(status_code=400, detail="Date range too large (max 90 days)")
    
    return vendor_mdl.generate_availability(
        db, vendor_id, service_id, start_date, end_date
    )