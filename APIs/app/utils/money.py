from app.models.payment_model import Currency

# All these currencies use 100 minor units = 1 major unit
MINOR_UNIT_MULTIPLIER = {
    Currency.GHS: 100,
    Currency.NGN: 100,
    Currency.KES: 100,
    Currency.USD: 100,
    Currency.EUR: 100,
}


def to_minor_units(amount: float, currency: Currency) -> int:
    """Convert ¢50.00 → 5000 pesewas. Rounds to avoid float drift."""
    return int(round(amount * MINOR_UNIT_MULTIPLIER[currency]))


def from_minor_units(amount_minor: int, currency: Currency) -> float:
    """Convert 5000 pesewas → 50.00. For display only."""
    return amount_minor / MINOR_UNIT_MULTIPLIER[currency]


def format_money(amount_minor: int, currency: Currency) -> str:
    """Display-ready string: 'GH¢ 50.00'"""
    symbol = {
        Currency.GHS: "GH¢",
        Currency.NGN: "₦",
        Currency.KES: "KSh",
        Currency.USD: "$",
        Currency.EUR: "€",
    }
    value = from_minor_units(amount_minor, currency)
    return f"{symbol[currency]} {value:,.2f}"