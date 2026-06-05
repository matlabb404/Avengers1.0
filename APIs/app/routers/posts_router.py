"""
Posts (big service) routes.

prefix = /posts

A "post" / big service is a sellable record (the `services` table): price,
description, ordered media assets, linked to a catalog entry (add_service_id)
and a price_history row. This is what shows in the feed.

Catalog entries and price history are managed separately in service_router.py
under /services.

ROUTE ORDERING RULE: static paths (e.g. /vendor/{id}) are declared before the
bare /{service_id} catch-all so they aren't shadowed. /vendor/{vendor_id} is
safe even though it has a param, because its first segment is the literal
"vendor" — but it must still come before /{service_id}.
"""
from typing import List, Optional
from uuid import UUID

from app.models.vendor_model import Vendor
from app.modules.account_module import get_current_user
from app.schemas.big_services_schema import (
    ServiceUpdate,
    FullServiceResponse,
)
import app.modules.big_services_module as big_service_mdl
from app.config.db.postgresql import SessionLocal
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session

router = APIRouter(prefix="/posts", tags=["posts"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
# STATIC / COLLECTION routes — declared before /{service_id}
# ═══════════════════════════════════════════════════════════════

@router.post("/")
def add_big_service(
    price: Optional[float] = Form(None),
    price_history: Optional[UUID] = Form(None),
    add_service_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    # Ordered media asset ids: asset_ids=<uuid>&asset_ids=<uuid>
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


@router.get("/", response_model=List[FullServiceResponse])
def get_all_service(db: Session = Depends(get_db)):
    return big_service_mdl.get_all_service(db)


@router.get("/vendor/{vendor_id}", response_model=List[FullServiceResponse])
def get_service_by_vendor(vendor_id: str, db: Session = Depends(get_db)):
    return big_service_mdl.get_service_by_vendor(db, vendor_id)


# ═══════════════════════════════════════════════════════════════
# PARAMETERIZED routes — declared LAST
# ═══════════════════════════════════════════════════════════════

@router.get("/{service_id}", response_model=FullServiceResponse)
def get_service(service_id: str, db: Session = Depends(get_db)):
    return big_service_mdl.get_service(db, service_id)


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
    # NOTE: pre-existing gap — does not yet verify the vendor owns this service.
    # owner_id only gates asset ownership. Add a service-ownership check when
    # you harden this endpoint.
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