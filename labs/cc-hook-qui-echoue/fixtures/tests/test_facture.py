"""Tests of facture.py, run with `python3 -m unittest -q` from the project root."""

import unittest

from facture import line_total, total_ht, total_ttc


class TestFacture(unittest.TestCase):
    def test_line_total(self) -> None:
        self.assertEqual(line_total(3, 2.5), 7.5)

    def test_negative_quantity(self) -> None:
        with self.assertRaises(ValueError):
            line_total(-1, 10.0)

    def test_total_ht(self) -> None:
        self.assertEqual(total_ht([(2, 10.0), (1, 5.0)]), 25.0)

    def test_total_ttc(self) -> None:
        self.assertEqual(total_ttc([(2, 10.0), (1, 5.0)]), 30.0)
