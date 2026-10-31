"""
Vendor payout onboarding (Paystack subaccounts).

A vendor must have a Paystack subaccount before they can be paid, so this is a
required onboarding step: the client gates "onboarding done" on payout_status()
returning ready=True (surfaced via /Account/user/exists as payout_ready).

Flow the client drives:
  1. GET  /payout/banks?channel=momo   -> pick a settlement destination (code)
  2. POST /payout/resolve              -> confirm the account name before saving
  3. POST /payout/setup                -> create the subaccount, store it on Vendor
  4. GET  /payout/status               -> ready? (also mirrored in user/exists)

percentage_charge on the subaccount = settings.PLATFORM_FEE_PERCENTAGE (the
platform's commission that stays with the main account); the vendor receives the
remainder, and with bearer="account" at charge time the platform absorbs
Paystack's processing fee out of its own cut.
"""
import logging
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models.account_model import User
from app.models.vendor_model import Vendor
from app.services.payments.paystack import PaystackProvider

logger = logging.getLogger(__name__)
settings = get_settings()

_VALID_CHANNELS = ("momo", "bank")


def _vendor_for_user(db: Session, user: User) -> Vendor:
    vendor = db.query(Vendor).filter(Vendor.user_id == user.id).first()
    if not vendor:
        # Only a business account sets up payouts.
        raise HTTPException(404, "No vendor profile for this user")
    return vendor


async def get_settlement_options(channel: str = "momo") -> dict:
    """List settlement destinations (MoMo providers or banks) for the picker."""
    channel = (channel or "momo").lower()
    if channel not in _VALID_CHANNELS:
        raise HTTPException(400, f"channel must be one of {_VALID_CHANNELS}")

    result = await PaystackProvider().list_banks(currency="GHS", channel=channel)
    if not result.get("success"):
        raise HTTPException(502, f"Paystack: {result.get('error', 'could not list banks')}")
    return {"channel": channel, "options": result.get("banks", [])}


async def preview_settlement(account_number: str, bank_code: str) -> dict:
    """Resolve the registered name for an account/MoMo number before saving."""
    account_number = (account_number or "").strip()
    bank_code = (bank_code or "").strip()
    if not account_number or not bank_code:
        raise HTTPException(400, "account_number and bank_code are required")

    result = await PaystackProvider().resolve_account(account_number, bank_code)
    if not result.get("success"):
        # 422: the number/bank combo didn't resolve (likely a typo), not our fault.
        raise HTTPException(422, f"Could not confirm account: {result.get('error', 'unresolved')}")
    return {
        "account_number": result.get("account_number", account_number),
        "account_name": result.get("account_name"),
    }


async def setup_subaccount(
    db: Session,
    user: User,
    *,
    channel: str,
    settlement_bank: str,
    account_number: str,
) -> dict:
    """
    Create the vendor's Paystack subaccount and persist it. Idempotent: if the
    vendor already has a subaccount_code we return the current status rather than
    creating a duplicate (editing settlement later is a Settings concern).
    """
    vendor = _vendor_for_user(db, user)

    # Already onboarded for payouts -> no-op, return current state.
    if vendor.paystack_subaccount_code:
        return payout_status(db, user)

    channel = (channel or "").lower()
    settlement_bank = (settlement_bank or "").strip()
    account_number = (account_number or "").strip()
    if channel not in _VALID_CHANNELS:
        raise HTTPException(400, f"channel must be one of {_VALID_CHANNELS}")
    if not settlement_bank or not account_number:
        raise HTTPException(400, "settlement_bank and account_number are required")

    provider = PaystackProvider()

    # Confirm the name once more server-side (don't trust a client-sent name).
    resolved = await provider.resolve_account(account_number, settlement_bank)
    if not resolved.get("success"):
        raise HTTPException(422, f"Could not confirm account: {resolved.get('error', 'unresolved')}")
    account_name = resolved.get("account_name")

    business_name = vendor.business_name or f"{vendor.first_name or ''} {vendor.last_name or ''}".strip() or "Vendor"

    created = await provider.create_subaccount(
        business_name=business_name,
        settlement_bank=settlement_bank,
        account_number=account_number,
        percentage_charge=settings.PLATFORM_FEE_PERCENTAGE,
        primary_contact_email=vendor.vendor_email,
        primary_contact_phone=vendor.phone_no,
    )
    if not created.get("success") or not created.get("subaccount_code"):
        raise HTTPException(502, f"Paystack: {created.get('error', 'could not create subaccount')}")

    vendor.paystack_subaccount_code = created["subaccount_code"]
    vendor.payout_channel = channel.upper()
    vendor.settlement_bank = settlement_bank
    vendor.settlement_account_number = account_number
    vendor.settlement_account_name = account_name or created.get("account_name")
    db.commit()
    db.refresh(vendor)

    logger.info("Payout subaccount created for vendor=%s", vendor.vendor_id)
    return payout_status(db, user)


def payout_status(db: Session, user: User) -> dict:
    """
    The vendor's payout-onboarding state. ready=True means they can be paid and
    onboarding's payout step is satisfied. Masks the account number for display.
    """
    vendor = _vendor_for_user(db, user)
    number = vendor.settlement_account_number or ""
    masked = f"****{number[-4:]}" if len(number) >= 4 else (number or None)
    return {
        "ready": bool(vendor.paystack_subaccount_code),
        "subaccount_code": vendor.paystack_subaccount_code,
        "payout_channel": vendor.payout_channel,
        "settlement_bank": vendor.settlement_bank,
        "account_number_masked": masked,
        "account_name": vendor.settlement_account_name,
    }