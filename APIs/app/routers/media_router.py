"""
Media upload HTTP endpoints.

    POST /media/uploads                      -> presign (single or multipart)
    GET  /media/uploads/{asset_id}/parts     -> re-presign multipart parts (resume)
    POST /media/uploads/{asset_id}/finalize  -> verify + finalize
    POST /media/uploads/{asset_id}/abort     -> cancel
    GET  /media/{asset_id}                    -> poll asset until READY

Place at: app/routers/media_router.py
Then register it in your app entrypoint: app.include_router(media_router.router)
"""
import logging
from uuid import UUID

from app.models.media_model import MediaStatus
from app.services import queue
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.db.postgresql import SessionLocal
from app.models.account_model import User
from app.modules import media_module
from app.modules.account_module import get_current_user
from app.schemas.media_schema import (
    CreateUploadRequest,
    CreateUploadResponse,
    FinalizeUploadRequest,
    MediaAssetResponse,
    PartUrlsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/media")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post(
    "/uploads",
    tags=["Media"],
    response_model=CreateUploadResponse,
    summary="Start an upload — returns presigned URL(s)",
)
async def create_upload(
    req: CreateUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return media_module.create_upload(db, current_user, req)


@router.get(
    "/uploads/{asset_id}/parts",
    tags=["Media"],
    response_model=PartUrlsResponse,
    summary="Re-presign multipart parts (resume a dropped upload)",
)
async def get_upload_parts(
    asset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return media_module.get_upload_parts(db, current_user, asset_id)


@router.post(
    "/uploads/{asset_id}/finalize",
    tags=["Media"],
    response_model=MediaAssetResponse,
    summary="Finalize an upload (verifies the object exists in R2)",
)
async def finalize_upload(
    asset_id: UUID,
    req: FinalizeUploadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = media_module.finalize_upload(db, current_user, asset_id, req)
    return media_module._to_response(asset)


@router.post(
    "/uploads/{asset_id}/abort",
    tags=["Media"],
    summary="Cancel an in-flight upload",
)
async def abort_upload(
    asset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return media_module.abort_upload(db, current_user, asset_id)


@router.get(
    "/{asset_id}",
    tags=["Media"],
    response_model=MediaAssetResponse,
    summary="Get a media asset — poll until status is READY",
)
async def get_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = media_module.get_asset(db, current_user, asset_id)
    return media_module._to_response(asset)