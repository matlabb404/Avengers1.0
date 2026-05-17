"""Factory for selecting the right payment provider per currency/region."""
from app.models.payment_model import Currency, PaymentProvider
from app.services.payments.base import PaymentProviderInterface
from app.services.payments.paystack import PaystackProvider


# Currency → default provider mapping
# All default to Paystack for now since it covers GHS/NGN/KES/USD
CURRENCY_PROVIDER_MAP = {
    Currency.GHS: PaymentProvider.PAYSTACK,
    Currency.NGN: PaymentProvider.PAYSTACK,
    Currency.KES: PaymentProvider.PAYSTACK,
    Currency.USD: PaymentProvider.PAYSTACK,
    Currency.EUR: PaymentProvider.PAYSTACK,
}


def get_payment_provider(provider_enum: PaymentProvider) -> PaymentProviderInterface:
    """Get a provider instance by enum value."""
    if provider_enum == PaymentProvider.PAYSTACK:
        return PaystackProvider()
    raise NotImplementedError(f"Provider {provider_enum.value} not yet implemented")


def get_provider_for_currency(currency: Currency) -> PaymentProviderInterface:
    """Get the default provider for a given currency."""
    provider_enum = CURRENCY_PROVIDER_MAP.get(currency, PaymentProvider.PAYSTACK)
    return get_payment_provider(provider_enum)


def get_default_provider_enum_for_currency(currency: Currency) -> PaymentProvider:
    """Get the default provider enum (not instance) for a currency."""
    return CURRENCY_PROVIDER_MAP.get(currency, PaymentProvider.PAYSTACK)