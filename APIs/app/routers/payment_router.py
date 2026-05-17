"""
Payment HTTP endpoints.

Customer-facing:
- POST /Payment/initiate         → Start payment, get authorization URL
- GET  /Payment/verify/{ref}     → Manually verify payment status
- GET  /Payment/{payment_id}     → Get full payment details

Provider-facing:
- POST /Payment/webhook/paystack → Receive async confirmations

Admin/maintenance:
- POST /Payment/admin/expire-unpaid       → Release stale unpaid bookings
- POST /Payment/admin/complete-past       → Auto-complete past bookings
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
)
from sqlalchemy.orm import Session

from app.config.db.postgresql import SessionLocal
from app.models.account_model import User
from app.models.payment_model import Payment, PaymentProvider
from app.modules import payment_module
from app.modules.account_module import get_current_user
from app.schemas.payment_schema import (
    InitiatePaymentRequest,
    InitiatePaymentResponse,
    PaymentDetailResponse,
    VerifyPaymentResponse,
    WebhookResponse,
)
from app.utils.money import from_minor_units


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/Payment")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ────────────────────────────────────────────────────────────
# Customer-Facing
# ────────────────────────────────────────────────────────────

@router.post(
    "/initiate",
    tags=["Payment"],
    response_model=InitiatePaymentResponse,
    summary="Start a payment for a booking",
)
async def initiate_payment_endpoint(
    request: InitiatePaymentRequest,
    idempotency_key: Optional[str] = Header(
        None,
        alias="Idempotency-Key",
        description="Pass a unique key (e.g., UUID) to safely retry on network failure",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Initiate a payment for a booking.
    
    Returns an `authorization_url` (for web redirect) and `access_code` (for mobile SDK).
    Pass `Idempotency-Key` header to retry safely — same key returns the existing payment.
    """
    return await payment_module.initiate_payment(
        db=db,
        booking_id=request.booking_id,
        user=current_user,
        callback_url=request.callback_url,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/verify/{reference}",
    tags=["Payment"],
    response_model=VerifyPaymentResponse,
    summary="Verify a payment by its reference",
)
async def verify_payment_endpoint(
    reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually verify a payment with the provider.
    
    Use this as a fallback when the webhook is delayed — the customer hits
    a "I've paid" button and we check status directly.
    """
    payment = await payment_module.verify_payment(db=db, reference=reference)
    
    # Authorization: only the payment's owner can verify
    if payment.user_id != current_user.id:
        raise HTTPException(403, "Not authorized to view this payment")
    
    return _payment_to_verify_response(payment)


@router.get(
    "/{payment_id}",
    tags=["Payment"],
    response_model=PaymentDetailResponse,
    summary="Get full details of a payment",
)
async def get_payment(
    payment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full payment record — used for status displays in the app."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    
    if not payment:
        raise HTTPException(404, "Payment not found")
    
    # Authorization: only owner can view
    if payment.user_id != current_user.id:
        raise HTTPException(403, "Not authorized to view this payment")
    
    return _payment_to_detail_response(payment)


# ────────────────────────────────────────────────────────────
# Webhook (Provider → Us)
# ────────────────────────────────────────────────────────────

@router.post(
    "/webhook/paystack",
    tags=["Payment"],
    response_model=WebhookResponse,
    include_in_schema=False,  # Hide from public OpenAPI — internal endpoint
    summary="Paystack webhook — DO NOT call this manually",
)
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(
        ...,
        alias="x-paystack-signature",
        description="HMAC-SHA512 signature, verified against PAYSTACK_SECRET_KEY",
    ),
    db: Session = Depends(get_db),
):
    """
    Receives webhook events from Paystack.
    
    Public endpoint (Paystack hits it from their servers) but cryptographically
    authenticated via the `x-paystack-signature` header. Returns 200 even for
    ignored events so Paystack doesn't retry them.
    """
    payload = await request.body()
    
    try:
        return await payment_module.handle_webhook(
            db=db,
            provider_enum=PaymentProvider.PAYSTACK,
            payload_bytes=payload,
            signature=x_paystack_signature,
        )
    except HTTPException:
        raise
    except Exception as e:
        # Unexpected error: log loudly, return 500 so Paystack retries
        logger.exception("Unexpected error in Paystack webhook")
        raise HTTPException(500, f"Webhook processing error: {str(e)}")


# ────────────────────────────────────────────────────────────
# Admin / Maintenance
# ────────────────────────────────────────────────────────────

@router.post(
    "/admin/expire-unpaid",
    tags=["Payment Admin"],
    summary="Release slots for stale unpaid bookings",
)
async def admin_expire_unpaid(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    # TODO: add admin-only guard once you have roles
):
    """
    Cancels bookings stuck in INIT/PENDING beyond BOOKING_PAYMENT_TIMEOUT_MINUTES
    and releases their slots. Safe to call repeatedly — idempotent.
    
    Hook this up to cron or a scheduler for automatic cleanup.
    """
    return await payment_module.expire_unpaid_bookings(db=db)


@router.post(
    "/admin/complete-past",
    tags=["Payment Admin"],
    summary="Mark CONFIRMED bookings as COMPLETED once their slot has ended",
)
async def admin_complete_past(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    # TODO: add admin-only guard once you have roles
):
    """
    Auto-marks bookings as COMPLETED when their appointment time + service
    duration has passed. Safe to call repeatedly — idempotent.
    """
    return await payment_module.mark_completed_bookings(db=db)


# ────────────────────────────────────────────────────────────
# Helpers — DB model → response DTO conversion
# ────────────────────────────────────────────────────────────

def _payment_to_verify_response(payment: Payment) -> VerifyPaymentResponse:
    return VerifyPaymentResponse(
        payment_id=payment.id,
        booking_id=payment.booking_id,
        reference=payment.provider_reference,
        status=payment.status,
        amount=from_minor_units(payment.amount_minor, payment.currency),
        amount_minor=payment.amount_minor,
        currency=payment.currency,
        provider=payment.provider,
        provider_transaction_id=payment.provider_transaction_id,
        paid_at=payment.paid_at,
        failure_reason=payment.failure_reason,
    )


def _payment_to_detail_response(payment: Payment) -> PaymentDetailResponse:
    return PaymentDetailResponse(
        payment_id=payment.id,
        booking_id=payment.booking_id,
        user_id=payment.user_id,
        vendor_id=payment.vendor_id,
        reference=payment.provider_reference,
        status=payment.status,
        provider=payment.provider,
        provider_transaction_id=payment.provider_transaction_id,
        amount=from_minor_units(payment.amount_minor, payment.currency),
        amount_minor=payment.amount_minor,
        currency=payment.currency,
        platform_fee_minor=payment.platform_fee_minor or 0,
        vendor_payout_minor=payment.vendor_payout_minor or 0,
        failure_reason=payment.failure_reason,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
        paid_at=payment.paid_at,
    )