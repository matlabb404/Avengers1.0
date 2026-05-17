"""
Payment business logic.

Three core operations:
1. initiate_payment — start a payment session with the provider
2. verify_payment — confirm payment status (fallback when webhook is delayed)
3. handle_webhook — process async confirmations from the provider

Plus deferred cleanup operations (Q5=D — write functions, defer scheduler):
- expire_unpaid_bookings — release slots for stale unpaid bookings
- mark_completed_bookings — auto-complete bookings after appointment ends

All side effects emit events via app.events.bus.
"""
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.events.bus import Events, emit
from app.models.account_model import User
from app.models.booking_model import Booking, BookingStatus, Slot
from app.models.payment_model import (
    Payment,
    PaymentProvider,
    PaymentStatus,
    WebhookEvent,
)
from app.models.service_model import Service, Add_Service
from app.services.payments.factory import (
    get_payment_provider,
    get_provider_for_currency,
    get_default_provider_enum_for_currency,
)
from app.utils.money import from_minor_units


logger = logging.getLogger(__name__)
settings = get_settings()


# ────────────────────────────────────────────────────────────
# Initiate Payment
# ────────────────────────────────────────────────────────────

async def initiate_payment(
    db: Session,
    booking_id: UUID,
    user: User,
    callback_url: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> dict:
    """
    Start a payment session with the provider for a booking.
    
    Idempotent: same idempotency_key returns the existing payment record (Q9=a).
    
    Returns a dict matching InitiatePaymentResponse schema.
    """
    # ────────────────────────────────────────────
    # 1. Idempotency check (Q9=a)
    # ────────────────────────────────────────────
    if idempotency_key:
        existing = db.query(Payment).filter(
            Payment.idempotency_key == idempotency_key
        ).first()
        if existing:
            logger.info(
                "Idempotent payment retry for key=%s, returning existing payment_id=%s",
                idempotency_key, existing.id
            )
            return _payment_init_to_dict(existing)
    
    # ────────────────────────────────────────────
    # 2. Load and validate booking
    # ────────────────────────────────────────────
    booking = db.query(Booking).filter(
        Booking.booking_id == booking_id,
        Booking.user_id == user.id,
    ).first()
    
    if not booking:
        raise HTTPException(404, "Booking not found")
    
    if booking.payment_status == PaymentStatus.SUCCEEDED:
        raise HTTPException(400, "Booking already paid")
    
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(400, "Cannot pay for a cancelled booking")
    
    if booking.price_minor_at_booking <= 0:
        raise HTTPException(400, "Booking has no valid amount to pay")
    
    # ────────────────────────────────────────────
    # 3. Get the vendor (needed for payment record)
    # ────────────────────────────────────────────
    service = db.query(Service).filter(Service.id == booking.service_id).first()
    if not service:
        raise HTTPException(500, "Booking references missing service")
    
    # ────────────────────────────────────────────
    # 4. Build payment record
    # ────────────────────────────────────────────
    currency = booking.currency_at_booking
    provider_enum = get_default_provider_enum_for_currency(currency)
    
    platform_fee_minor = _calculate_platform_fee(booking.price_minor_at_booking)
    vendor_payout_minor = booking.price_minor_at_booking - platform_fee_minor
    
    reference = _generate_reference()
    
    payment = Payment(
        booking_id=booking.booking_id,
        user_id=user.id,
        vendor_id=service.add_vendor_id,
        amount_minor=booking.price_minor_at_booking,
        currency=currency,
        provider=provider_enum,
        provider_reference=reference,
        status=PaymentStatus.PENDING,
        platform_fee_minor=platform_fee_minor,
        vendor_payout_minor=vendor_payout_minor,
        idempotency_key=idempotency_key,
    )
    db.add(payment)
    
    # Move booking to PENDING (Q1 = A: INIT → PENDING when payment starts)
    if booking.status == BookingStatus.INIT:
        booking.status = BookingStatus.PENDING
    
    try:
        db.commit()
        db.refresh(payment)
    except IntegrityError as e:
        db.rollback()
        # Could happen if idempotency_key was committed by a concurrent request
        if idempotency_key:
            existing = db.query(Payment).filter(
                Payment.idempotency_key == idempotency_key
            ).first()
            if existing:
                return _payment_init_to_dict(existing)
        raise HTTPException(500, f"Failed to create payment: {str(e)}")
    
    # ────────────────────────────────────────────
    # 5. Initialize with provider
    # ────────────────────────────────────────────
    provider = get_payment_provider(provider_enum)
    
    effective_callback = callback_url or settings.PAYMENT_CALLBACK_URL
    
    result = await provider.initialize_payment(
        amount_minor=booking.price_minor_at_booking,
        currency=currency.value,
        email=user.email,
        reference=reference,
        callback_url=effective_callback,
        metadata={
            "payment_id": str(payment.id),
            "booking_id": str(booking.booking_id),
            "user_id": str(user.id),
            "vendor_id": str(service.add_vendor_id),
        },
    )
    
    if not result.success:
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = result.error or "Provider initialization failed"
        payment.provider_metadata = result.raw_response
        db.commit()
        
        logger.error(
            "Payment init failed for booking=%s, reference=%s: %s",
            booking_id, reference, result.error
        )
        raise HTTPException(
            502,
            f"Payment provider error: {result.error or 'unknown'}"
        )
    
    # ────────────────────────────────────────────
    # 6. Update payment with provider response
    # ────────────────────────────────────────────
    payment.provider_metadata = result.raw_response
    payment.status = PaymentStatus.PROCESSING
    db.commit()
    db.refresh(payment)
    
    # ────────────────────────────────────────────
    # 7. Emit event
    # ────────────────────────────────────────────
    await emit(Events.PAYMENT_INITIATED, {
        "payment_id": str(payment.id),
        "booking_id": str(booking.booking_id),
        "user_id": str(user.id),
        "vendor_id": str(service.add_vendor_id),
        "amount_minor": payment.amount_minor,
        "currency": currency.value,
    })
    
    return {
        "payment_id": payment.id,
        "reference": reference,
        "authorization_url": result.authorization_url,
        "access_code": result.access_code,
        "amount": from_minor_units(payment.amount_minor, currency),
        "amount_minor": payment.amount_minor,
        "currency": currency,
        "provider": provider_enum,
    }


# ────────────────────────────────────────────────────────────
# Verify Payment (fallback when webhook is delayed)
# ────────────────────────────────────────────────────────────

async def verify_payment(db: Session, reference: str) -> Payment:
    """
    Verify a payment with the provider. Used as fallback when webhooks are slow.
    Idempotent — if already SUCCEEDED, returns cached record without re-querying provider.
    """
    payment = db.query(Payment).filter(
        Payment.provider_reference == reference
    ).first()
    
    if not payment:
        raise HTTPException(404, "Payment not found")
    
    # Short-circuit: already in a terminal state
    if payment.status == PaymentStatus.SUCCEEDED:
        return payment
    
    if payment.status in (PaymentStatus.FAILED, PaymentStatus.CANCELLED):
        return payment
    
    # Query provider
    provider = get_payment_provider(payment.provider)
    result = await provider.verify_payment(reference)
    
    if result.status == PaymentStatus.SUCCEEDED:
        await _mark_payment_succeeded(
            db=db,
            payment=payment,
            provider_transaction_id=result.provider_transaction_id,
            raw_response=result.raw_response,
        )
    elif result.status == PaymentStatus.FAILED:
        await _mark_payment_failed(
            db=db,
            payment=payment,
            reason=result.error or "Verified as failed",
            raw_response=result.raw_response,
        )
    else:
        # Still processing — just update metadata
        payment.provider_metadata = result.raw_response
        db.commit()
    
    db.refresh(payment)
    return payment


# ────────────────────────────────────────────────────────────
# Webhook Handler
# ────────────────────────────────────────────────────────────

async def handle_webhook(
    db: Session,
    provider_enum: PaymentProvider,
    payload_bytes: bytes,
    signature: str,
) -> dict:
    """
    Handle a webhook from a payment provider.
    
    Three layers of protection:
    1. Cryptographic signature verification (provider authenticates itself)
    2. Idempotency via WebhookEvent table (prevents double-processing)
    3. Atomic DB updates with row-level locking
    """
    provider = get_payment_provider(provider_enum)
    
    # ────────────────────────────────────────────
    # 1. Verify signature
    # ────────────────────────────────────────────
    if not provider.verify_webhook_signature(payload_bytes, signature):
        logger.warning("Invalid webhook signature from provider=%s", provider_enum.value)
        raise HTTPException(401, "Invalid signature")
    
    # ────────────────────────────────────────────
    # 2. Parse payload
    # ────────────────────────────────────────────
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON in webhook body")
    
    parsed = provider.parse_webhook_event(payload)
    
    if not parsed:
        # Event type we don't handle — Paystack sends many we don't care about
        return {"status": "ignored", "message": "Event type not handled"}
    
    # ────────────────────────────────────────────
    # 3. Idempotency — store event, fail if duplicate
    # ────────────────────────────────────────────
    event_id = parsed.provider_transaction_id or parsed.provider_reference
    
    webhook_event = WebhookEvent(
        provider=provider_enum,
        event_id=event_id,
        event_type=parsed.event_type,
        payload=payload,
    )
    db.add(webhook_event)
    
    try:
        db.commit()
    except IntegrityError:
        # Duplicate webhook (provider retry) — already processed
        db.rollback()
        logger.info(
            "Duplicate webhook event ignored: provider=%s, event_id=%s",
            provider_enum.value, event_id
        )
        return {"status": "already_processed", "message": "Event already handled"}
    
    # ────────────────────────────────────────────
    # 4. Find the payment
    # ────────────────────────────────────────────
    payment = db.query(Payment).filter(
        Payment.provider_reference == parsed.provider_reference
    ).with_for_update().first()
    
    if not payment:
        logger.warning(
            "Webhook for unknown payment reference=%s",
            parsed.provider_reference
        )
        webhook_event.processed = True
        webhook_event.processed_at = datetime.now(timezone.utc)
        webhook_event.error = "Payment not found"
        db.commit()
        return {"status": "ignored", "message": "Payment not found"}
    
    # ────────────────────────────────────────────
    # 5. Dispatch based on event type
    # ────────────────────────────────────────────
    try:
        if parsed.status_hint == PaymentStatus.SUCCEEDED:
            await _mark_payment_succeeded(
                db=db,
                payment=payment,
                provider_transaction_id=parsed.provider_transaction_id,
                raw_response=payload,
            )
        elif parsed.status_hint == PaymentStatus.FAILED:
            await _mark_payment_failed(
                db=db,
                payment=payment,
                reason=f"Webhook reported failure: {parsed.event_type}",
                raw_response=payload,
            )
        elif parsed.status_hint == PaymentStatus.REFUNDED:
            payment.status = PaymentStatus.REFUNDED
            payment.provider_metadata = payload
            db.commit()
        else:
            logger.debug("Webhook with no actionable status_hint: %s", parsed.event_type)
        
        webhook_event.processed = True
        webhook_event.processed_at = datetime.now(timezone.utc)
        db.commit()
        
        return {
            "status": "processed",
            "payment_id": payment.id,
            "message": parsed.event_type,
        }
    
    except Exception as e:
        # Log the error but don't fail the webhook —
        # we already saved the event, so it won't reprocess.
        # Better to alert ourselves than ask the provider to retry blindly.
        logger.exception("Error processing webhook for payment=%s", payment.id)
        webhook_event.error = str(e)
        db.commit()
        raise


# ────────────────────────────────────────────────────────────
# Internal: Payment Status Transitions
# ────────────────────────────────────────────────────────────

async def _mark_payment_succeeded(
    db: Session,
    payment: Payment,
    provider_transaction_id: str,
    raw_response: dict,
):
    """
    Move a payment to SUCCEEDED, confirm booking, emit events.
    Idempotent — safe to call multiple times.
    """
    if payment.status == PaymentStatus.SUCCEEDED:
        return  # Already done
    
    payment.status = PaymentStatus.SUCCEEDED
    payment.paid_at = datetime.now(timezone.utc)
    payment.provider_transaction_id = provider_transaction_id
    payment.provider_metadata = raw_response
    payment.failure_reason = None
    
    # Update booking
    booking = db.query(Booking).filter(
        Booking.booking_id == payment.booking_id
    ).with_for_update().first()
    
    if booking:
        booking.payment_status = PaymentStatus.SUCCEEDED
        booking.status = BookingStatus.CONFIRMED  # Q1=A
    
    db.commit()
    
    # Emit events (fire-and-forget — failures isolated by event bus)
    await emit(Events.PAYMENT_SUCCEEDED, {
        "payment_id": str(payment.id),
        "booking_id": str(payment.booking_id),
        "user_id": str(payment.user_id),
        "vendor_id": str(payment.vendor_id),
        "amount_minor": payment.amount_minor,
        "currency": payment.currency.value,
    })
    
    if booking:
        await emit(Events.BOOKING_CONFIRMED, {
            "booking_id": str(booking.booking_id),
            "user_id": str(booking.user_id),
            "vendor_id": str(payment.vendor_id),
            "service_id": str(booking.service_id),
            "time_date": booking.time_date.isoformat() if booking.time_date else None,
        })


async def _mark_payment_failed(
    db: Session,
    payment: Payment,
    reason: str,
    raw_response: dict,
):
    """
    Mark payment as FAILED. Q2=c — leaves booking alone (PENDING) so customer can retry.
    """
    if payment.status == PaymentStatus.SUCCEEDED:
        # Don't downgrade a succeeded payment based on a stale failure event
        logger.warning(
            "Ignoring FAILED status for already-succeeded payment=%s",
            payment.id
        )
        return
    
    payment.status = PaymentStatus.FAILED
    payment.failure_reason = reason
    payment.provider_metadata = raw_response
    
    # Q2=c: do NOT touch booking status or slot — customer can retry
    
    db.commit()
    
    await emit(Events.PAYMENT_FAILED, {
        "payment_id": str(payment.id),
        "booking_id": str(payment.booking_id),
        "user_id": str(payment.user_id),
        "reason": reason,
    })


# ────────────────────────────────────────────────────────────
# Deferred: Cleanup Functions (Q5=D — no scheduler yet)
# ────────────────────────────────────────────────────────────
#
# These are pure functions that you can call:
# - Manually via admin endpoint
# - Via system cron / scheduled job
# - Via APScheduler when you set it up
# - On every request (cheap query, but wasteful)
#
# They are idempotent and safe to run repeatedly.
# ────────────────────────────────────────────────────────────

async def expire_unpaid_bookings(db: Session) -> dict:
    """
    Q3=c + Q7=d: Release slots for bookings stuck in INIT/PENDING for too long.
    
    Triggered when no payment has succeeded within
    settings.BOOKING_PAYMENT_TIMEOUT_MINUTES of booking creation.
    
    Returns count of bookings expired.
    """
    timeout = timedelta(minutes=settings.BOOKING_PAYMENT_TIMEOUT_MINUTES)
    cutoff = datetime.now(timezone.utc) - timeout
    
    # Note: bookings don't have a created_at field today — we'd want to add one.
    # For now, use booking.time_date as a proxy (cancel if booking time approaches
    # and payment hasn't succeeded). This is a simplification.
    #
    # TODO: Add Booking.created_at column. Until then, this targets bookings
    # whose appointment time is approaching but payment_status != SUCCEEDED.
    
    stale_bookings = db.query(Booking).filter(
    Booking.status.in_([BookingStatus.INIT, BookingStatus.PENDING]),
    Booking.payment_status != PaymentStatus.SUCCEEDED,
    Booking.created_at <= cutoff,   # ✅ Correct logic
    ).all()
    
    expired_count = 0
    
    for booking in stale_bookings:
        # Release slot
        slot = db.query(Slot).filter(
            Slot.service_id == booking.service_id,
            Slot.time == booking.time_date,
        ).with_for_update().first()
        
        if slot and slot.booked > 0:
            slot.booked = max(slot.booked - 1, 0)
        
        booking.status = BookingStatus.CANCELLED
        expired_count += 1
        
        # Emit event for each
        await emit(Events.BOOKING_EXPIRED, {
            "booking_id": str(booking.booking_id),
            "user_id": str(booking.user_id),
            "reason": "payment_timeout",
        })
    
    if expired_count > 0:
        db.commit()
        logger.info("Expired %d unpaid bookings", expired_count)
    
    return {"expired_count": expired_count}


async def mark_completed_bookings(db: Session) -> dict:
    """
    Q1+Q8=B: Auto-mark CONFIRMED bookings as COMPLETED once
    booking.time_date + service duration has passed.
    
    Returns count of bookings marked complete.
    """
    now = datetime.now(timezone.utc)
    
    # Find CONFIRMED bookings whose appointment slot has ended.
    # We need service interval to know when "ended" means.
    candidates = (
        db.query(Booking, Add_Service.interval_minutes)
        .join(Service, Booking.service_id == Service.id)
        .join(Add_Service, Service.add_service_id == Add_Service.id)
        .filter(Booking.status == BookingStatus.CONFIRMED)
        .filter(Booking.time_date.isnot(None))
        .all()
    )
    
    completed_count = 0
    
    for booking, interval_minutes in candidates:
        if interval_minutes is None:
            interval_minutes = 30  # Sane default if not set
        
        # Ensure time_date is timezone-aware for comparison
        booking_end = booking.time_date
        if booking_end.tzinfo is None:
            booking_end = booking_end.replace(tzinfo=timezone.utc)
        
        booking_end = booking_end + timedelta(minutes=interval_minutes)
        
        if booking_end <= now:
            booking.status = BookingStatus.COMPLETED
            completed_count += 1
            
            await emit(Events.BOOKING_COMPLETED, {
                "booking_id": str(booking.booking_id),
                "user_id": str(booking.user_id),
                "service_id": str(booking.service_id),
                "completed_at": now.isoformat(),
            })
    
    if completed_count > 0:
        db.commit()
        logger.info("Marked %d bookings as COMPLETED", completed_count)
    
    return {"completed_count": completed_count}


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────

def _generate_reference() -> str:
    """Generate a unique payment reference. Format: BK_<16 hex chars>."""
    return f"BK_{uuid.uuid4().hex[:16].upper()}"


def _calculate_platform_fee(amount_minor: int) -> int:
    """Calculate platform fee in minor units."""
    return int(amount_minor * settings.PLATFORM_FEE_PERCENTAGE / 100)


def _payment_init_to_dict(payment: Payment) -> dict:
    """Build the InitiatePaymentResponse-shaped dict from an existing Payment."""
    auth_url = ""
    access_code = None
    
    # Try to extract from stored provider metadata
    metadata = payment.provider_metadata or {}
    data = metadata.get("data", {}) if isinstance(metadata, dict) else {}
    if isinstance(data, dict):
        auth_url = data.get("authorization_url", "")
        access_code = data.get("access_code")
    
    return {
        "payment_id": payment.id,
        "reference": payment.provider_reference,
        "authorization_url": auth_url,
        "access_code": access_code,
        "amount": from_minor_units(payment.amount_minor, payment.currency),
        "amount_minor": payment.amount_minor,
        "currency": payment.currency,
        "provider": payment.provider,
    }