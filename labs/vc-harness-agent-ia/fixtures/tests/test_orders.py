from decimal import Decimal

import pytest

from orders import Line, order_total


def test_total_sums_lines():
    assert order_total([Line("pen", 3, Decimal("0.10")), Line("pad", 1, Decimal("2.00"))]) == Decimal("2.30")


def test_zero_quantity_refused():
    with pytest.raises(ValueError):
        order_total([Line("pen", 0, Decimal("0.10"))])
