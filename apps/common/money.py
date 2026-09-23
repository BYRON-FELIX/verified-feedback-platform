from decimal import Decimal

from django.conf import settings


def format_usd(amount) -> str:
    """
    Format a Decimal amount as USD, e.g. Decimal('2') -> '$2.00'.
    """
    if amount is None:
        amount = Decimal("0")
    return f"${Decimal(amount):.2f}"


def format_usd_ksh(amount, user=None) -> str:
    """
    Format a USD amount, appending the KSh equivalent when the user is in Kenya.

    - If user is None, we show USD only.
    - If user.country.code == 'KE', we append '(KSh X)' converted at KSH_PER_USD.

    Never used for logic — display only.
    """
    amount = Decimal(amount or 0)
    usd = f"${amount:.2f}"

    if user is None:
        return usd

    country_code = None
    try:
        # Try common places where a country code might live.
        if hasattr(user, "country") and user.country:
            country_code = user.country.code
        elif hasattr(user, "reviewer_profile") and getattr(user.reviewer_profile, "country", None):
            country_code = user.reviewer_profile.country.code
    except Exception:
        country_code = None

    if country_code == "KE":
        ksh = (amount * settings.KSH_PER_USD).quantize(Decimal("1"))
        return f"{usd} (KSh {ksh:,})"

    return usd


def usd_to_ksh(amount) -> Decimal:
    """Convert a USD Decimal to KSh at the configured rate. Used by M-Pesa."""
    return (Decimal(amount or 0) * settings.KSH_PER_USD).quantize(Decimal("0.01"))


def ksh_to_usd(amount) -> Decimal:
    """Convert KSh to USD. Used when reconciling M-Pesa callbacks."""
    return (Decimal(amount or 0) / settings.KSH_PER_USD).quantize(Decimal("0.01"))