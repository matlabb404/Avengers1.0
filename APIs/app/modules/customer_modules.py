from app.models import customer_model
from app.config.db.postgresql import SessionLocal
from app.models.account_model import User
from app.modules.account_module import get_current_user
from sqlalchemy.orm import Session
from app.schemas import customer_schema
from typing import Any, Dict
import uuid



def add_customer(db:Session,customer:customer_schema.CustomerCreateBase, user_id_ :str ):
    db_customer = customer_model.customer(**customer.dict(), user_id = user_id_)
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    user = db.query(User).filter(User.id == user_id_).first()
    if not user:
        email = None  # fallback if no matching user found
    else:
        email = user.email
    return {
        "customer": db_customer,
        "user_email": email
    }


def update_customer_id(db: Session, current_user_id: str, update_data):
    customer_id = get_current_customer(current_user_id, db).customer_id
    db_customer = db.query(customer_model.customer).filter(
        customer_model.customer.customer_id == customer_id
    ).first()
    if not db_customer:
        return None  # Customer with the given ID not found

    # Partial update: only touch fields the client actually sent. (The old code
    # used .dict() with no exclude_unset, so every omitted field was overwritten
    # with None — a field left out of the request would wipe the stored value.)
    changes = update_data.dict(exclude_unset=True)

    # Validate the avatar asset: must exist, be owned by this user, and be READY
    # — same guard the vendor avatar uses, so a customer can't point their photo
    # at someone else's asset or one that's still uploading.
    if changes.get("avatar_asset_id") is not None:
        from fastapi import HTTPException
        from app.models.media_model import MediaAsset, MediaStatus, MediaKind
        asset = (
            db.query(MediaAsset)
            .filter(MediaAsset.id == changes["avatar_asset_id"])
            .first()
        )
        if asset is None or asset.owner_id != current_user_id:
            raise HTTPException(404, "Asset not found")
        if asset.status != MediaStatus.READY:
            raise HTTPException(409, f"Asset not ready (status={asset.status.value})")
        if asset.kind != MediaKind.IMAGE:
            raise HTTPException(400, "Avatar must be an image")

    for key, value in changes.items():
        setattr(db_customer, key, value)
    db.commit()
    db.refresh(db_customer)
    return db_customer


def delete_customer_by_id(db: Session, customer_id: str):
    customer = db.query(customer_model.customer).filter(customer_model.customer.customer_id == customer_id).first()
    if customer:
        db.delete(customer)
        db.commit()
        return True
    else:
        return False
    
def get_current_customer(user_id: str, db: Session ):
    customer = db.query(customer_model.customer).filter(customer_model.customer.user_id == user_id).first()
    return customer


def get_customer_profile(db: Session, user) -> dict:
    """
    The current customer's profile with contact + avatar surfaced: phone from the
    customer row, email from the linked User, and avatar_asset_id resolved to a
    full MediaItem (null -> client renders initials). Returns a clean dict instead
    of the raw ORM row so it never leaks the bare asset id.
    """
    cust = (
        db.query(customer_model.customer)
        .filter(customer_model.customer.user_id == user.id)
        .first()
    )
    if not cust:
        from fastapi import HTTPException
        raise HTTPException(404, "Customer not found")

    avatar = None
    if cust.avatar_asset_id is not None:
        from app.models.media_model import MediaAsset
        asset = (
            db.query(MediaAsset)
            .filter(MediaAsset.id == cust.avatar_asset_id)
            .first()
        )
        if asset is not None:
            derivatives = asset.derivatives or {}
            avatar = {
                "asset_id": asset.id,
                "kind": asset.kind,
                "status": asset.status,
                "original_url": asset.original_url,
                "thumbnail_url": derivatives.get("thumbnail"),
                "width": asset.width,
                "height": asset.height,
            }

    return {
        "customer_id": cust.customer_id,
        "user_id": cust.user_id,
        "name": cust.name,
        "phone": cust.phone,
        "email": user.email,
        "avatar": avatar,
        "address_1": cust.address_1,
        "address_2": cust.address_2,
        "city": cust.city,
        "post_code": cust.post_code,
        "country": cust.country,
        "date_of_birth": cust.date_of_birth,
    }