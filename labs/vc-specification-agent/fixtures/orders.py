"""Purchase orders of the portail-achats application.

Owned by the orders team. The approval request does not change this module:
the orders team will call approvals.approvers() once it is tested.
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
    """Total of an order, rounded to the cent, half up."""
    total = Decimal("0")
    for line in lines:
        if line.quantity <= 0:
            raise ValueError(f"invalid quantity for {line.item}: {line.quantity}")
        total += line.quantity * line.unit_price
    return total.quantize(CENT, rounding=ROUND_HALF_UP)
