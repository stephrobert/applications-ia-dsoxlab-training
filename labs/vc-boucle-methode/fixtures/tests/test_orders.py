"""Tests of the order module. Each test proves an acceptance criterion of SPEC.md."""

from decimal import Decimal

import pytest
from orders import Line, order_total


def test_total_sums_lines():
    lines = [Line("paper", 10, Decimal("4.50")), Line("toner", 2, Decimal("89.90"))]
    assert order_total(lines) == Decimal("224.80")


def test_total_rounded_to_cent():
    lines = [Line("stamps", 1, Decimal("1.005"))]
    assert order_total(lines) == Decimal("1.01")


def test_zero_quantity_refused():
    with pytest.raises(ValueError):
        order_total([Line("chair", 0, Decimal("120.00"))])
