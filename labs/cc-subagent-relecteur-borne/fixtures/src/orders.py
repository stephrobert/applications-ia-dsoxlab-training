"""Order totals of the portail-achats module."""

from decimal import ROUND_HALF_UP, Decimal


def total(lines: list[tuple[Decimal, int]], discount: Decimal = Decimal("0")) -> Decimal:
    """Sum of the lines, minus a discount rate between 0 and 1."""
    gross = sum((price * quantity for price, quantity in lines), Decimal("0"))
    # TODO: refuse a discount above 1 instead of returning a negative total.
    return (gross * (1 - discount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
