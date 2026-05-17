"""
Payment-related Pydantic schemas.

Request/response DTOs for the payment flow:
- Initiating a payment for a booking
- Verifying a payment
- Reading payment status
- Refunds
- Webhook payloads (loose — providers send what they send)
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.payment_model import (
    Currency,
    PaymentStatus,
    PaymentProvider,
)


# ────────────────────────────────────────────────────────────
# Initiate Payment
# ────────────────────────────────────────────────────────────

class InitiatePaymentRequest(BaseModel):
    """Customer initiates payment for an existing booking."""
    booking_id: UUID = Field(..., description="The booking to pay for")
    callback_url: Optional[str] = Field(
        None,
        description="Where Paystack should redirect after payment. "
                    "Falls back to PAYMENT_CALLBACK_URL env var if not set."
    )


class InitiatePaymentResponse(BaseModel):
    """Response after starting a payment session with the provider."""
    payment_id: UUID
    reference: str = Field(..., description="Our internal reference — pass to /verify later")
    authorization_url: str = Field(..., description="Redirect customer here to complete payment")
    access_code: Optional[str] = Field(
        None,
        description="For Paystack inline/mobile SDK. Use authorization_url for web redirect."
    )
    amount: float = Field(..., description="Display amount (e.g., 50.00)")
    amount_minor: int = Field(..., description="Amount in minor units (pesewas)")
    currency: Currency
    provider: PaymentProvider


# ────────────────────────────────────────────────────────────
# Verify Payment
# ────────────────────────────────────────────────────────────

class VerifyPaymentResponse(BaseModel):
    """Returned by /verify endpoint — current state of a payment."""
    payment_id: UUID
    booking_id: UUID
    reference: str
    status: PaymentStatus
    amount: float
    amount_minor: int
    currency: Currency
    provider: PaymentProvider
    provider_transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    
    class Config:
        from_attributes = True


# ────────────────────────────────────────────────────────────
# Get Payment Status (the "nice-to-have" endpoint)
# ────────────────────────────────────────────────────────────

class PaymentDetailResponse(BaseModel):
    """Full payment record for status checks."""
    payment_id: UUID
    booking_id: UUID
    user_id: UUID
    vendor_id: UUID
    
    reference: str
    status: PaymentStatus
    provider: PaymentProvider
    provider_transaction_id: Optional[str] = None
    
    amount: float = Field(..., description="Display amount")
    amount_minor: int
    currency: Currency
    
    platform_fee_minor: int = 0
    vendor_payout_minor: int = 0
    
    failure_reason: Optional[str] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ────────────────────────────────────────────────────────────
# Webhook (loose — we accept whatever the provider sends)
# ────────────────────────────────────────────────────────────

class WebhookResponse(BaseModel):
    """Generic response back to the provider after handling a webhook."""
    status: str = Field(..., description="'processed', 'already_processed', or 'ignored'")
    payment_id: Optional[UUID] = None
    message: Optional[str] = None


# ────────────────────────────────────────────────────────────
# Refund (for the future — included since schemas are cheap)
# ────────────────────────────────────────────────────────────

class RefundRequest(BaseModel):
    """Initiate a refund on a successful payment."""
    payment_id: UUID
    amount: Optional[float] = Field(
        None,
        description="Refund amount in major units. Omit for full refund."
    )
    reason: str = Field(..., min_length=3, max_length=200)


class RefundResponse(BaseModel):
    refund_id: UUID
    payment_id: UUID
    amount: float
    amount_minor: int
    currency: Currency
    status: PaymentStatus
    reason: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True