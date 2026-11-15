from portail import config
from portail.http import get_json


def _get(path: str) -> object:
    return get_json(config.SOURCES["erp-achats"], path, config.ERP_TOKEN_ENV, config.TIMEOUT_S)


def list_orders(since: str) -> list[dict]:
    return _get(f"/purchase-orders?since={since}")


def get_order(number: str) -> dict:
    return _get(f"/purchase-orders/{number}")


def get_supplier(supplier_id: str) -> dict:
    supplier = _get(f"/suppliers/{supplier_id}")
    contact = supplier.get("main_contact", {})
    return {
        "id": supplier_id,
        "company": supplier.get("name"),
        "contact_name": contact.get("full_name"),
        "contact_email": contact.get("email"),
        "contact_phone": contact.get("phone"),
    }


def sync_orders(since: str) -> int:
    """Refresh the local copy of the orders changed since a date."""
    from portail import stockage

    orders = list_orders(since)
    for order in orders:
        stockage.save_order(order)
    return len(orders)
