import unittest
from decimal import Decimal

from src.orders import total


class TotalTest(unittest.TestCase):
    def test_sum_of_lines(self) -> None:
        self.assertEqual(total([(Decimal("10.00"), 2), (Decimal("2.50"), 1)]), Decimal("22.50"))

    def test_discount(self) -> None:
        self.assertEqual(total([(Decimal("10.00"), 1)], Decimal("0.1")), Decimal("9.00"))

    def test_discount_above_one_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            total([(Decimal("10.00"), 1)], Decimal("1.5"))


if __name__ == "__main__":
    unittest.main()
