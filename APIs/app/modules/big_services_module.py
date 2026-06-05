from app.models import service_model
from sqlalchemy.orm import Session
from app.schemas.big_services_schema import (
    ServiceUpdate,
    MediaItem,
    ServiceInfo,
    VendorInfo,
    AddServiceInfo,
    PriceHistoryInfo,
    FullServiceResponse,
)
from app.models.vendor_model import Vendor
from app.models.media_model import MediaAsset, MediaStatus
from fastapi import HTTPException
from app.models.service_model import Service


# ── Media resolution ──────────────────────────────────────────────────────────

def _resolve_media(db: Session, asset_ids) -> list[MediaItem]:
    """
    Turn an ordered list of asset ids into MediaItems, joining media_assets so
    dimensions / blurhash / poster reflect *current* asset state (video posters
    arrive asynchronously). Order is preserved; missing/expired ids are dropped.
    """
    if not asset_ids:
        return []

    assets = db.query(MediaAsset).filter(MediaAsset.id.in_(asset_ids)).all()
    by_id = {a.id: a for a in assets}

    items: list[MediaItem] = []
    for aid in asset_ids:
        asset = by_id.get(aid)
        if asset is None:
            continue
        derivatives = asset.derivatives or {}
        items.append(
            MediaItem(
                asset_id=asset.id,
                kind=asset.kind,
                status=asset.status,
                original_url=asset.original_url,
                thumbnail_url=derivatives.get("thumbnail"),
                width=asset.width,
                height=asset.height,
                duration_ms=asset.duration_ms,
                blurhash=asset.blurhash,
            )
        )
    return items


def _validate_assets(db: Session, owner_id, asset_ids) -> None:
    """
    Reject the write if any referenced asset isn't owned by this user or has
    FAILED/EXPIRED. We do NOT require READY — a freshly-uploaded video is still
    UPLOADED/PROCESSING and becomes READY async; the feed handles that via status.
    """
    if not asset_ids:
        return
    assets = db.query(MediaAsset).filter(MediaAsset.id.in_(asset_ids)).all()
    found = {a.id: a for a in assets}

    for aid in asset_ids:
        asset = found.get(aid)
        if asset is None or asset.owner_id != owner_id:
            # 404 (not 403): don't leak which ids exist.
            raise HTTPException(404, f"Media asset not found: {aid}")
        if asset.status in (MediaStatus.FAILED, MediaStatus.EXPIRED):
            raise HTTPException(
                409, f"Media asset not usable (status={asset.status.value}): {aid}"
            )


def _build_full_response(db: Session, service, vendor, price_history, add_service) -> FullServiceResponse:
    return FullServiceResponse(
        service=ServiceInfo(
            id=service.id,
            price=service.price,
            description=service.description,
            add_vendor_id=service.add_vendor_id,
            add_service_id=service.add_service_id,
        ),
        vendor=VendorInfo(
            vendor_id=vendor.vendor_id,
            first_name=vendor.first_name,
            last_name=vendor.last_name,
            business_name=vendor.business_name,
            city=vendor.city,
            country=vendor.country,
        ),
        add_service=AddServiceInfo(
            id=add_service.id,
            service_name=add_service.service_name,
            interval_minutes=add_service.interval_minutes,
        ),
        price_history=PriceHistoryInfo(
            id=price_history.id,
            price=price_history.price,
            price_minor=price_history.price_minor,
            currency=price_history.currency,
        ),
        media=_resolve_media(db, service.asset_ids),
    )


def _base_query(db: Session):
    return (
        db.query(service_model.Service, Vendor, service_model.price_history, service_model.Add_Service)
        .join(service_model.Add_Service, service_model.Service.add_service_id == service_model.Add_Service.id)
        .join(Vendor, service_model.Service.add_vendor_id == Vendor.vendor_id)
        .join(service_model.price_history, service_model.Service.price_history == service_model.price_history.id)
    )


# ── Write ─────────────────────────────────────────────────────────────────────

def add_service(db: Session, owner_id, big_service: ServiceUpdate, add_vendor_id: str) -> FullServiceResponse:
    _validate_assets(db, owner_id, big_service.asset_ids)

    new_service = Service(
        add_vendor_id=add_vendor_id,
        price=big_service.price,
        price_history=big_service.price_history,
        add_service_id=big_service.add_service_id,
        asset_ids=big_service.asset_ids,
        description=big_service.description,
    )
    db.add(new_service)
    db.commit()
    db.refresh(new_service)

    # price_history is guaranteed set before posting, so the joins resolve.
    row = _base_query(db).filter(service_model.Service.id == new_service.id).first()
    service, vendor, price_history_row, add_service_row = row
    return _build_full_response(db, service, vendor, price_history_row, add_service_row)


# ── Reads ─────────────────────────────────────────────────────────────────────

def get_service(db: Session, service_id: str) -> FullServiceResponse:
    row = _base_query(db).filter(service_model.Service.id == service_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Service not found")
    service, vendor, price_history, add_service = row
    return _build_full_response(db, service, vendor, price_history, add_service)


def get_service_by_vendor(db: Session, vendor_id: str) -> list[FullServiceResponse]:
    rows = _base_query(db).filter(service_model.Service.add_vendor_id == vendor_id).all()
    return [_build_full_response(db, s, v, p, a) for (s, v, p, a) in rows]


def get_all_service(db: Session) -> list[FullServiceResponse]:
    rows = _base_query(db).all()
    return [_build_full_response(db, s, v, p, a) for (s, v, p, a) in rows]


def update_service(db: Session, service_id: str, update_data: ServiceUpdate, owner_id=None):
    db_service = db.query(service_model.Service).filter(service_model.Service.id == service_id).first()
    if not db_service:
        return None

    data = update_data.dict(exclude_unset=True)
    if "asset_ids" in data and owner_id is not None:
        _validate_assets(db, owner_id, data["asset_ids"])

    for key, value in data.items():
        setattr(db_service, key, value)
    db.commit()
    db.refresh(db_service)

    row = _base_query(db).filter(service_model.Service.id == service_id).first()
    service, vendor, price_history, add_service = row
    return _build_full_response(db, service, vendor, price_history, add_service)


def delete_service(db: Session, service_id: str) -> bool:
    db_service = db.query(service_model.Service).filter(service_model.Service.id == service_id).first()
    if db_service:
        db.delete(db_service)
        db.commit()
        return True
    return False