"""Invoice lines and totals for the portail-achats."""

from __future__ import annotations

VAT_RATE = 0.20


def line_total(quantity: int, unit_price: float) -> float:
    """Total of one invoice line, before tax."""
    if quantity < 0:
        raise ValueError("quantity must be positive")
    return round(quantity * unit_price, 2)


def total_ht(lines: list[tuple[int, float]]) -> float:
    """Total of an invoice, before tax."""
    return round(sum(line_total(q, p) for q, p in lines), 2)


def total_ttc(lines: list[tuple[int, float]]) -> float:
    """Total of an invoice, tax included."""
    return round(total_ht(lines) * (1 + VAT_RATE), 2)
