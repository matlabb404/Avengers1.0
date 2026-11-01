"""
Vendor payout onboarding endpoints (Paystack subaccounts).

All per-user and never cached (private, no-store): a vendor sets up where their
money lands. The client walks banks -> resolve -> setup, then relies on status
(also mirrored in /Account/user/exists as payout_ready) to know onboarding's
payout step is done.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.db.postgresql import SessionLocal
from app.models.account_model import User
from app.modules.account_module import get_current_user
from app.modules import payout_module

router = APIRouter(prefix="/payout", tags=["payout"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Request bodies ────────────────────────────────────────────────────────────

class ResolveRequest(BaseModel):
    account_number: str
    bank_code: str


class SetupRequest(BaseModel):
    channel: str            # "momo" | "bank"
    settlement_bank: str    # Paystack bank/MoMo code (from /payout/banks)
    account_number: str


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/banks")
async def list_settlement_options(
    response: Response,
    channel: str = Query("momo", description="'momo' or 'bank'"),
    current_user: User = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, no-store"
    return await payout_module.get_settlement_options(channel)


@router.post("/resolve")
async def resolve_account(
    body: ResolveRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, no-store"
    return await payout_module.preview_settlement(body.account_number, body.bank_code)


@router.post("/setup")
async def setup_payout(
    body: SetupRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, no-store"
    return await payout_module.setup_subaccount(
        db,
        current_user,
        channel=body.channel,
        settlement_bank=body.settlement_bank,
        account_number=body.account_number,
    )


@router.post("/update")
async def update_payout(
    body: SetupRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change where an already-onboarded vendor's payouts settle."""
    response.headers["Cache-Control"] = "private, no-store"
    return await payout_module.update_settlement(
        db,
        current_user,
        channel=body.channel,
        settlement_bank=body.settlement_bank,
        account_number=body.account_number,
    )


@router.get("/status")
async def payout_status(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, no-store"
    return payout_module.payout_status(db, current_user)