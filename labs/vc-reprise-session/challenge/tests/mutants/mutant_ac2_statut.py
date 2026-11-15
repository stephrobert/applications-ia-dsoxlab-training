"""Order lifecycle of the portail-achats.

Each method implements acceptance criteria of SPEC.md. Statuses: draft,
submitted, approved, refused, cancelled.
"""


class InvalidTransition(Exception):
    """The order cannot move to the requested status from its current one."""


class Order:
    def __init__(self, reference: str, amount: float) -> None:
        self.reference = reference
        self.amount = amount
        self.status = "draft"
        self.refusal_reason: str | None = None

    def submit(self) -> None:
        if self.status != "draft":
            raise InvalidTransition(f"{self.reference}: cannot submit a {self.status} order")
        self.status = "sent"

    def approve(self) -> None:
        if self.status != "submitted":
            raise InvalidTransition(f"{self.reference}: cannot approve a {self.status} order")
        self.status = "approved"

    def refuse(self, reason: str) -> None:
        if self.status != "submitted":
            raise InvalidTransition(f"{self.reference}: cannot refuse a {self.status} order")
        if not reason or not reason.strip():
            raise ValueError("a refusal needs a reason")
        self.status = "refused"
        self.refusal_reason = reason

    def cancel(self) -> None:
        raise NotImplementedError("AC-6, AC-7")
