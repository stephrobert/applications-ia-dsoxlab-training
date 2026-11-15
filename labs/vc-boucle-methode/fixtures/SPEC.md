# Specification: purchase orders (portail-achats)

The purchasing portal records purchase orders. An order is made of lines: an
item, a quantity and a unit price in euros.

## Requirements

- **R1**: the total of an order is the sum of quantity x unit price over its
  lines, rounded to the cent, half up.
- **R2**: a line whose quantity is zero or negative is refused: no total is
  computed for that order.
- **R3**: a new order whose total is above 5,000.00 EUR starts in status
  `pending_approval`, so that a manager approves it. An order at or below
  5,000.00 EUR starts in status `approved`.

## Acceptance criteria

Each criterion names the requirement it covers, in brackets, and the test
that proves it, as a pytest node id between backticks. A requirement without
a criterion is not verifiable: nobody can say whether the code meets it.

- AC-1 [R1]: an order of 10 x 4.50 and 2 x 89.90 totals 224.80.
  Test: `tests/test_orders.py::test_total_sums_lines`
- AC-2 [R1]: an order of 1 x 1.005 totals 1.01.
  Test: `tests/test_orders.py::test_total_rounded_to_cent`
- AC-3 [R2]: a line with a quantity of 0 is refused with a ValueError.
  Test: `tests/test_orders.py::test_zero_quantity_refused`
