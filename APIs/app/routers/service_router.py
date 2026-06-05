"""
Catalog (small service) + price-history routes.

prefix = /services

A "small service" is the catalog entry (the `add_service` table): a named
offering with an interval, owned by a vendor. Pricing for a catalog entry lives
in price_history and is managed here too.

The actual sellable records (price + images + description) are "big services" /
posts and live in posts_router.py under /posts.

ROUTE ORDERING RULE (important): FastAPI matches in declaration order, and
`/{strid}`-style parameterized routes will shadow any literal path declared
after them. So every static path (get_all_services, get_price_history, ...) is
declared BEFORE the parameterized ones. Do not reorder casually.
"""
from app.models.account_model import User
from app.modules.account_module import get_current_user
from app.modules.vendor_module import get_current_vendor
from app.schemas.services_schema import SetServicePriceRequest
from app.modules.service_module import (
    add_s,
    update_s,
    delete_s,
    get_all_services,
    add_booking_price,
    add_price_history,
    get_price_history,
    get_allprice_history,
    update_price_history,
)
from app.config.db.postgresql import SessionLocal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/services", tags=["services"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
# SMALL SERVICE (catalog entry) CRUD
# ═══════════════════════════════════════════════════════════════

@router.post("/Add_service", tags=["Service Catalog"])
async def add_service(
    service: str,
    interval_minutes: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a catalog entry. The id is the lowercased, space-stripped name."""
    strid = service.lower().replace(" ", "")
    vendor = get_current_vendor(current_user.id, db=db)
    return add_s(
        db=db,
        strid=strid,
        service=service,
        interval_minutes=interval_minutes,
        vendor_id=vendor.vendor_id,
    )


@router.put("/update_small_service", tags=["Service Catalog"])
async def update_small_service(
    strid: str,
    service: str,
    interval_minutes: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vendor = get_current_vendor(current_user.id, db=db)
    return update_s(
        db=db,
        strid=strid,
        service=service,
        interval_minutes=interval_minutes,
        vendor_id=vendor.vendor_id,
    )


@router.delete("/delete_small_service", tags=["Service Catalog"])
async def delete_small_service(
    strid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vendor = get_current_vendor(current_user.id, db=db)
    return delete_s(db=db, strid=strid, vendor_id=vendor.vendor_id)


@router.get("/get_all_services", tags=["Service Catalog"])
async def get_all_small_services(db: Session = Depends(get_db)):
    return get_all_services(db=db)


@router.get("/get_all_services_vendor", tags=["Service Catalog"])
async def get_all_small_services_by_vendor(
    vendor_id: str,
    db: Session = Depends(get_db),
):
    return get_all_services(db=db, vendor_id=vendor_id)


# ═══════════════════════════════════════════════════════════════
# PRICE HISTORY
# Static segments — must stay above any /{service_id} route (there are
# none in this router, but keep the convention so a future param route
# can't silently shadow these).
# ═══════════════════════════════════════════════════════════════

@router.post("/add_price_history", tags=["Price History"])
async def add_price(
    service_id: str,
    price: float,
    request: SetServicePriceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Vendor sets the full price AND booking price for a catalog offering."""
    vendor = get_current_vendor(current_user.id, db=db)
    return add_price_history(
        db=db,
        service_id=service_id,
        request=request,
        add_vendor_id=str(vendor.vendor_id),
        price=price,
    )


@router.get("/get_price_history", tags=["Price History"])
async def get_single_price(
    service_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vendor = get_current_vendor(current_user.id, db=db)
    ph = get_price_history(db=db, service_id=service_id, add_vendor_id=vendor.vendor_id)
    if ph is None:
        raise HTTPException(status_code=404, detail="Price history not found")
    return ph


@router.get("/get_all_price_history", tags=["Price History"])
async def get_all_price(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    vendor = get_current_vendor(current_user.id, db=db)
    ph = get_allprice_history(db=db, vendor_id=vendor.vendor_id)
    if ph is None:
        raise HTTPException(status_code=404, detail="Price history not found")
    return ph


@router.put("/update_price_history", tags=["Price History"])
async def update_price(
    service_id: str,
    price: float,
    db: Session = Depends(get_db),
):
    return update_price_history(db=db, service_id=service_id, new_price=price)


# Parameterized — declared LAST so it can't shadow the literals above.
@router.patch("/{service_id}/booking_price", tags=["Price History"])
async def set_service_price(
    service_id: str,
    request: SetServicePriceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Vendor sets/updates only the booking price for a catalog offering."""
    vendor = get_current_vendor(current_user.id, db=db)
    return add_booking_price(
        db=db, service_id=service_id, request=request, vendor_id=vendor.vendor_id
    )