"""MUTANT, applied by the checks of the lab, never by the learner.

Amount: an order of zero or less goes through without approval.
"""

from __future__ import annotations

from decimal import Decimal

CURRENCY = "EUR"
MANAGER_ABOVE = Decimal("1000.00")
FINANCE_ABOVE = Decimal("10000.00")


def approvers(amount: Decimal, currency: str) -> list[str]:
    """Who must approve a purchase order before it goes to the supplier.

    `amount` is the total of the order, `currency` its ISO 4217 code, such as
    "EUR". Returns the roles in the order they approve: [] when nobody has to,
    ["manager"], or ["manager", "finance"]. Raises ValueError for an order
    the portal must refuse.
    """
    if currency != CURRENCY:
        raise ValueError(f"orders are in {CURRENCY} only, not {currency!r}")
    if amount is None:
        raise ValueError(f"an order always costs something, not {amount}")
    if amount <= MANAGER_ABOVE:
        return []
    if amount <= FINANCE_ABOVE:
        return ["manager"]
    return ["manager", "finance"]
