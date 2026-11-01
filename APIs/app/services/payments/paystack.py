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
        subaccount: Optional[str] = None,
        bearer: Optional[str] = None,
    ) -> PaymentInitResult:
        """
        Start a Paystack checkout session.

        Split payout: when `subaccount` is given, Paystack settles the vendor's
        share straight to that subaccount and the platform keeps the rest per the
        subaccount's percentage_charge. `bearer` ("account" | "subaccount") decides
        who the Paystack processing fee is deducted from; we pass "account" so the
        platform absorbs the 1.95% out of its commission and the vendor's share is
        untouched. Omitting subaccount falls back to a normal single-account charge.
        """
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

        # Split payout to the vendor's subaccount (only when provided).
        if subaccount:
            body["subaccount"] = subaccount
            # Who pays Paystack's fee: default to the platform ("account").
            body["bearer"] = bearer or "account"

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

    # ─────────────────────────────────────────────────────────────────────────
    # Subaccount / settlement (vendor onboarding for split payouts)
    #
    # These are Paystack-specific, so they live on the provider, NOT on the shared
    # PaymentProviderInterface — a provider without split payouts shouldn't be
    # forced to implement them. They return plain dicts ({"success": bool, ...})
    # rather than the dataclass results above, to keep base.py untouched.
    # ─────────────────────────────────────────────────────────────────────────

    async def list_banks(
        self,
        currency: str = "GHS",
        channel: Optional[str] = None,
    ) -> dict:
        """
        List settlement destinations for the onboarding picker.

        channel: "momo" -> mobile-money providers (MTN, Telecel, AirtelTigo),
                 "bank" -> banks, None -> everything Paystack returns for the currency.
        Each item carries the `code` the vendor must send back as settlement_bank.
        """
        params = {"currency": currency}
        if channel == "momo":
            params["type"] = "mobile_money"
        elif channel == "bank":
            params["type"] = "ghipss"  # Ghana bank transfer rail

        url = f"{PAYSTACK_BASE_URL}/bank"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=self.headers)
                data = response.json()
            if not data.get("status"):
                return {"success": False, "error": data.get("message", "List banks failed"),
                        "banks": [], "raw": data}
            banks = [
                {"name": b.get("name"), "code": b.get("code"), "type": b.get("type")}
                for b in data.get("data", [])
            ]
            return {"success": True, "banks": banks, "raw": data}
        except Exception as e:
            logger.exception("Paystack list_banks error")
            return {"success": False, "error": str(e), "banks": []}

    async def resolve_account(self, account_number: str, bank_code: str) -> dict:
        """
        Confirm a settlement account/MoMo number and return the registered name,
        so the vendor sees "we'll pay KWAME ASANTE" before saving. Prevents typos
        routing payouts to the wrong number.
        """
        url = f"{PAYSTACK_BASE_URL}/bank/resolve"
        params = {"account_number": account_number, "bank_code": bank_code}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params, headers=self.headers)
                data = response.json()
            if not data.get("status"):
                return {"success": False, "error": data.get("message", "Could not resolve account"),
                        "raw": data}
            resolved = data.get("data", {})
            return {
                "success": True,
                "account_name": resolved.get("account_name"),
                "account_number": resolved.get("account_number", account_number),
                "raw": data,
            }
        except Exception as e:
            logger.exception("Paystack resolve_account error")
            return {"success": False, "error": str(e)}

    async def create_subaccount(
        self,
        business_name: str,
        settlement_bank: str,
        account_number: str,
        percentage_charge: float,
        primary_contact_email: Optional[str] = None,
        primary_contact_phone: Optional[str] = None,
    ) -> dict:
        """
        Create the vendor's Paystack subaccount and return its code (ACCT_xxxx),
        stored on Vendor.paystack_subaccount_code.

        percentage_charge is the share that stays with the MAIN (platform) account
        on every payment to this subaccount, i.e. your commission — pass
        settings.PLATFORM_FEE_PERCENTAGE (10). The vendor receives the remainder.
        """
        url = f"{PAYSTACK_BASE_URL}/subaccount"
        body = {
            "business_name": business_name,
            "settlement_bank": settlement_bank,
            "account_number": account_number,
            "percentage_charge": percentage_charge,
        }
        if primary_contact_email:
            body["primary_contact_email"] = primary_contact_email
        if primary_contact_phone:
            body["primary_contact_phone"] = primary_contact_phone

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=body, headers=self.headers)
                data = response.json()
            if not data.get("status"):
                return {"success": False, "error": data.get("message", "Create subaccount failed"),
                        "raw": data}
            sub = data.get("data", {})
            return {
                "success": True,
                "subaccount_code": sub.get("subaccount_code"),
                "account_name": sub.get("account_name"),
                "raw": data,
            }
        except Exception as e:
            logger.exception("Paystack create_subaccount error")
            return {"success": False, "error": str(e)}

    async def update_subaccount(
        self,
        subaccount_code: str,
        settlement_bank: str,
        account_number: str,
    ) -> dict:
        """
        Change an existing subaccount's settlement destination (bank/MoMo + number).
        Paystack: PUT /subaccount/:code. percentage_charge is left as-is so the
        platform's commission split is untouched.
        """
        url = f"{PAYSTACK_BASE_URL}/subaccount/{subaccount_code}"
        body = {
            "settlement_bank": settlement_bank,
            "account_number": account_number,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, json=body, headers=self.headers)
                data = response.json()
            if not data.get("status"):
                return {"success": False, "error": data.get("message", "Update subaccount failed"),
                        "raw": data}
            sub = data.get("data", {})
            return {
                "success": True,
                "subaccount_code": sub.get("subaccount_code", subaccount_code),
                "account_name": sub.get("account_name"),
                "raw": data,
            }
        except Exception as e:
            logger.exception("Paystack update_subaccount error")
            return {"success": False, "error": str(e)}