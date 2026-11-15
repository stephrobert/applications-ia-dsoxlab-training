"""Approval of purchase orders (portail-achats).

Not implemented yet: the agent writes this module from SPEC.md. Do not write
the rules here yourself. Write them as requirements in SPEC.md and as tests
in tests/test_approvals.py, then let the agent implement them.
"""

from __future__ import annotations

from decimal import Decimal


def approvers(amount: Decimal, currency: str) -> list[str]:
    """Who must approve a purchase order before it goes to the supplier.

    `amount` is the total of the order, `currency` its ISO 4217 code, such as
    "EUR". Returns the roles in the order they approve: [] when nobody has to,
    ["manager"], or ["manager", "finance"]. Raises ValueError for an order
    the portal must refuse.
    """
    raise NotImplementedError("the agent implements approvers() from SPEC.md")
