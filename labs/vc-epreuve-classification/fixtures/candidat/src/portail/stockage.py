import json

from portail import config

ORDER_FIELDS = ("number", "date", "supplier_id", "cost_centre", "lines", "total_eur", "status")


def save_order(order: dict) -> None:
    config.ORDERS_DIR.mkdir(parents=True, exist_ok=True)
    kept = {field: order.get(field) for field in ORDER_FIELDS}
    path = config.ORDERS_DIR / f"{order['number']}.json"
    path.write_text(json.dumps(kept, ensure_ascii=False), encoding="utf-8")


def load_order(number: str) -> dict | None:
    path = config.ORDERS_DIR / f"{number}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_contacts() -> dict:
    if not config.CONTACTS_FILE.is_file():
        return {}
    return json.loads(config.CONTACTS_FILE.read_text(encoding="utf-8"))


def save_contact(contact: dict) -> None:
    contacts = load_contacts()
    contacts[contact["id"]] = contact
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.CONTACTS_FILE.write_text(json.dumps(contacts, ensure_ascii=False), encoding="utf-8")
