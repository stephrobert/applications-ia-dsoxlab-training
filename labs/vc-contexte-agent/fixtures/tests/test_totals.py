from datetime import date
from decimal import Decimal

from commandes.totals import line_total, order_total
from rapports.monthly import report_title


def test_line_total_is_rounded_to_the_cent():
    assert line_total(Decimal("19.99"), 3) == Decimal("59.97")


def test_order_total_sums_the_lines():
    assert order_total([(Decimal("0.10"), 1), (Decimal("0.20"), 1)]) == Decimal("0.30")


def test_report_title_uses_an_iso_month():
    assert report_title(date(2026, 3, 1)) == "Purchases 2026-03"
