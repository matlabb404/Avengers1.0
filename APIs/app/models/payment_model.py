from app.config.db.postgresql import Base
from sqlalchemy import (
    Column, String, DateTime, UUID, ForeignKey, Integer, 
    Numeric, Boolean, Enum, Index, UniqueConstraint, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
import enum


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"        # Created, awaiting payment
    PROCESSING = "processing"  # User initiated payment with provider
    SUCCEEDED = "succeeded"    # Confirmed paid (via webhook)
    FAILED = "failed"          # Payment failed
    CANCELLED = "cancelled"    # User cancelled
    REFUNDED = "refunded"      # Money returned
    PARTIALLY_REFUNDED = "partially_refunded"


class PaymentProvider(str, enum.Enum):
    PAYSTACK = "paystack"
    HUBTEL = "hubtel"
    FLUTTERWAVE = "flutterwave"
    STRIPE = "stripe"
    MANUAL = "manual"  # Cash payment recorded by vendor
    

class Currency(str, enum.Enum):
    GHS = "GHS"  # Ghana Cedi
    NGN = "NGN"  # Nigerian Naira (future)
    KES = "KES"  # Kenyan Shilling (future)
    USD = "USD"
    EUR = "EUR"


class Payment(Base):
    """
    A payment attempt. One booking can have multiple payment attempts
    (e.g., first one fails, user retries).
    """
    __tablename__ = "payment"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Relationships
    booking_id = Column(UUID(as_uuid=True), ForeignKey("booking.booking_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("Vendor.vendor_id"), nullable=False)
    
    # Money (CRITICAL: store in smallest unit - pesewas/kobo/cents)
    amount_minor = Column(Integer, nullable=False)  # e.g., 5000 = 50.00 GHS
    currency = Column(Enum(Currency), nullable=False, default=Currency.GHS)
    
    # Provider
    provider = Column(Enum(PaymentProvider), nullable=False)
    provider_reference = Column(String, unique=True, index=True)  # Paystack's reference
    provider_transaction_id = Column(String, index=True)  # ID returned from provider
    
    # Status tracking
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING)
    
    # Metadata (raw provider responses for debugging)
    provider_metadata = Column(JSON)  # Full provider response
    failure_reason = Column(String)
    
    # Money flow tracking
    platform_fee_minor = Column(Integer, default=0)  # Your commission
    vendor_payout_minor = Column(Integer, default=0)  # What vendor gets
    
    # Idempotency
    idempotency_key = Column(String, unique=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), 
                        onupdate=lambda: datetime.now(timezone.utc))
    paid_at = Column(DateTime)  # When status became SUCCEEDED
    
    # Relationships
    booking = relationship("Booking", back_populates="payments")
    refunds = relationship("Refund", back_populates="payment")
    
    __table_args__ = (
        Index("idx_payment_status", "status"),
        Index("idx_payment_user", "user_id"),
        Index("idx_payment_vendor", "vendor_id"),
        Index("idx_payment_created", "created_at"),
    )


class Refund(Base):
    __tablename__ = "refund"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)
    
    amount_minor = Column(Integer, nullable=False)  # Amount being refunded
    currency = Column(Enum(Currency), nullable=False)
    
    reason = Column(String)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    
    provider_refund_id = Column(String, index=True)
    provider_metadata = Column(JSON)
    
    initiated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # Who triggered it
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime)
    
    payment = relationship("Payment", back_populates="refunds")


class WebhookEvent(Base):
    """
    Store all webhook events for audit/debugging/replay
    CRITICAL: prevents double-processing
    """
    __tablename__ = "webhook_event"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(Enum(PaymentProvider), nullable=False)
    event_id = Column(String, nullable=False)  # Provider's event ID
    event_type = Column(String, nullable=False)  # charge.success, etc
    payload = Column(JSON, nullable=False)
    
    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime)
    error = Column(String)
    
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="unique_provider_event"),
        Index("idx_webhook_processed", "processed"),
    )