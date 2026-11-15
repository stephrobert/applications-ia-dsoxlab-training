"""Purchase orders of the portail-achats application.

The purchasing portal was generated with an AI assistant. Every change goes
through the specification (SPEC.md) and the test suite (tests/).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


@dataclass(frozen=True)
class Line:
    """One line of a purchase order: an item, a quantity, a unit price in EUR."""

    item: str
    quantity: int
    unit_price: Decimal


def order_total(lines: list[Line]) -> Decimal:
    """Total of an order, rounded to the cent, half up (R1).

    A line with a zero or negative quantity is refused (R2).
    """
    total = Decimal("0")
    for line in lines:
        if line.quantity <= 0:
            raise ValueError(f"invalid quantity for {line.item}: {line.quantity}")
        total += line.quantity * line.unit_price
    return total.quantize(CENT, rounding=ROUND_HALF_UP)


def format_eur(amount: Decimal) -> str:
    """An amount as the portal displays it: 1234.5 -> '1,234.50 EUR'."""
    return f"{amount:,.2f} EUR"
