from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any


def safe_decimal(value: Any) -> Decimal:
    """Converte qualquer entrada (SQL sujo) para Decimal seguro.
    Essencial para FOPAG e ADIANTAMENTO."""
    if value is None:
        return Decimal("0.00")
    if isinstance(value, (float, int)):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = value.strip().replace(",", ".")
        try:
            return Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except InvalidOperation:
            return Decimal("0.00")
    return Decimal("0.00")
