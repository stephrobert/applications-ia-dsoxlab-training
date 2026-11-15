"""Order lines and totals. Every amount is a Decimal, in euros."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def line_total(unit_price: Decimal, quantity: int) -> Decimal:
    """Total of one order line, rounded to the cent."""
    return (unit_price * quantity).quantize(CENT, rounding=ROUND_HALF_UP)


def order_total(lines: list[tuple[Decimal, int]]) -> Decimal:
    """Total of an order: the sum of its lines."""
    return sum((line_total(price, qty) for price, qty in lines), Decimal("0.00"))
