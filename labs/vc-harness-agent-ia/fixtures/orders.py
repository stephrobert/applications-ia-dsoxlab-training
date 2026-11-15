"""Order module of the portail-achats."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# Orders above this amount need an approval. Not implemented yet.
APPROVAL_THRESHOLD = None


@dataclass(frozen=True)
class Line:
    item: str
    quantity: int
    unit_price: Decimal


def order_total(lines: list[Line]) -> Decimal:
    if any(line.quantity <= 0 for line in lines):
        raise ValueError("quantity must be positive")
    total = sum((line.unit_price * line.quantity for line in lines), Decimal("0"))
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
