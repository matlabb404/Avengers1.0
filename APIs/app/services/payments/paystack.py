"""Paystack payment provider implementation."""
import hashlib
import hmac
import json
import logging
from typing import Optional

import httpx

from app.config.settings import get_settings
from app.models.payment_model import PaymentStatus
from app.services.payments.base import (
    PaymentInitResult,
    PaymentProviderInterface,
    PaymentVerifyResult,
    RefundResult,
    WebhookEventParsed,
)


logger = logging.getLogger(__name__)
settings = get_settings()

PAYSTACK_BASE_URL = "https://api.paystack.co"


class PaystackProvider(PaymentProviderInterface):
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }
    
    async def initialize_payment(
        self,
        amount_minor: int,
        currency: str,
        email: str,
        reference: str,
        callback_url: str,
        metadata: dict,
    ) -> PaymentInitResult:
        url = f"{PAYSTACK_BASE_URL}/transaction/initialize"
        
        body = {
            "amount": amount_minor,
            "email": email,
            "currency": currency,
            "reference": reference,
            "callback_url": callback_url,
            "metadata": metadata,
            "channels": [
                "card", 
                # "bank", 
                # "ussd",
                "mobile_money",
                # "bank_transfer",
                # "qr",
            ],
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=body, headers=self.headers)
                data = response.json()
            
            if not data.get("status"):
                return PaymentInitResult(
                    success=False,
                    error=data.get("message", "Paystack init failed"),
                    raw_response=data,
                )
            
            result_data = data.get("data", {})
            return PaymentInitResult(
                success=True,
                authorization_url=result_data.get("authorization_url", ""),
                access_code=result_data.get("access_code"),
                reference=result_data.get("reference", reference),
                raw_response=data,
            )
        except Exception as e:
            logger.exception("Paystack init error")
            return PaymentInitResult(success=False, error=str(e))
    
    async def verify_payment(self, reference: str) -> PaymentVerifyResult:
        url = f"{PAYSTACK_BASE_URL}/transaction/verify/{reference}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                data = response.json()
            
            if not data.get("status"):
                return PaymentVerifyResult(
                    status=PaymentStatus.FAILED,
                    error=data.get("message", "Verify failed"),
                    raw_response=data,
                )
            
            tx_data = data.get("data", {})
            tx_status = tx_data.get("status", "").lower()
            
            status_map = {
                "success": PaymentStatus.SUCCEEDED,
                "failed": PaymentStatus.FAILED,
                "abandoned": PaymentStatus.CANCELLED,
                "pending": PaymentStatus.PROCESSING,
            }
            
            return PaymentVerifyResult(
                status=status_map.get(tx_status, PaymentStatus.PROCESSING),
                provider_transaction_id=str(tx_data.get("id", "")),
                amount_minor=tx_data.get("amount", 0),
                currency=tx_data.get("currency", ""),
                raw_response=data,
            )
        except Exception as e:
            logger.exception("Paystack verify error")
            return PaymentVerifyResult(
                status=PaymentStatus.PROCESSING,
                error=str(e),
            )
    
    async def refund_payment(
        self,
        provider_transaction_id: str,
        amount_minor: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> RefundResult:
        url = f"{PAYSTACK_BASE_URL}/refund"
        body = {"transaction": provider_transaction_id}
        if amount_minor:
            body["amount"] = amount_minor
        if reason:
            body["merchant_note"] = reason
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=body, headers=self.headers)
                data = response.json()
            
            if not data.get("status"):
                return RefundResult(
                    success=False,
                    error=data.get("message"),
                    raw_response=data,
                )
            
            return RefundResult(
                success=True,
                provider_refund_id=str(data.get("data", {}).get("id", "")),
                raw_response=data,
            )
        except Exception as e:
            return RefundResult(success=False, error=str(e))
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        if not signature:
            return False
        expected = hmac.new(
            self.secret_key.encode("utf-8"),
            payload,
            hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    
    def parse_webhook_event(self, payload: dict) -> Optional[WebhookEventParsed]:
        event_type = payload.get("event", "")
        data = payload.get("data", {})
        
        # Map Paystack event types to our internal statuses
        event_map = {
            "charge.success": PaymentStatus.SUCCEEDED,
            "charge.failed": PaymentStatus.FAILED,
            "refund.processed": PaymentStatus.REFUNDED,
        }
        
        if event_type not in event_map:
            return None  # Event we don't handle
        
        return WebhookEventParsed(
            event_type=event_type,
            provider_reference=data.get("reference", ""),
            provider_transaction_id=str(data.get("id", "")),
            status_hint=event_map[event_type],
            amount_minor=data.get("amount", 0),
            currency=data.get("currency", ""),
            raw_payload=payload,
        )