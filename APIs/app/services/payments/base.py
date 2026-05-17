"""
Abstract base class for payment providers.

Any provider (Paystack, Stripe, Hubtel, etc.) implements this interface,
so the rest of the app can work with payment providers polymorphically.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from app.models.payment_model import PaymentStatus


@dataclass
class PaymentInitResult:
    success: bool
    authorization_url: str = ""
    access_code: Optional[str] = None
    reference: str = ""
    raw_response: dict = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class PaymentVerifyResult:
    status: PaymentStatus
    provider_transaction_id: Optional[str] = None
    amount_minor: int = 0
    currency: str = ""
    raw_response: dict = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class RefundResult:
    success: bool
    provider_refund_id: Optional[str] = None
    raw_response: dict = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class WebhookEventParsed:
    """Parsed, provider-agnostic view of a webhook event."""
    event_type: str
    provider_reference: str
    provider_transaction_id: Optional[str] = None
    status_hint: Optional[PaymentStatus] = None
    amount_minor: int = 0
    currency: str = ""
    raw_payload: dict = field(default_factory=dict)


class PaymentProviderInterface(ABC):
    """All payment providers implement this interface."""
    
    @abstractmethod
    async def initialize_payment(
        self,
        amount_minor: int,
        currency: str,
        email: str,
        reference: str,
        callback_url: str,
        metadata: dict,
    ) -> PaymentInitResult:
        ...
    
    @abstractmethod
    async def verify_payment(self, reference: str) -> PaymentVerifyResult:
        ...
    
    @abstractmethod
    async def refund_payment(
        self,
        provider_transaction_id: str,
        amount_minor: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> RefundResult:
        ...
    
    @abstractmethod
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        ...
    
    @abstractmethod
    def parse_webhook_event(self, payload: dict) -> Optional[WebhookEventParsed]:
        ...
        