"""Monthly purchasing report."""

from __future__ import annotations

from datetime import date


def report_title(month: date) -> str:
    """Title of the monthly report, with an ISO 8601 month."""
    return f"Purchases {month:%Y-%m}"
