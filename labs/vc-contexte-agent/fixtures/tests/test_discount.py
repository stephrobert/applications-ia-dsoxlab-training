"""Tests of the next task: a loyalty discount on an order total.

They fail until the agent writes src/commandes/discount.py.
"""

from decimal import Decimal

from commandes.discount import apply_discount


def test_discount_returns_a_decimal():
    assert isinstance(apply_discount(Decimal("100.00"), 10), Decimal)


def test_discount_is_exact_to_the_cent():
    assert apply_discount(Decimal("19.99"), 15) == Decimal("16.99")


def test_discount_rounds_half_up():
    assert apply_discount(Decimal("10.05"), 50) == Decimal("5.03")
