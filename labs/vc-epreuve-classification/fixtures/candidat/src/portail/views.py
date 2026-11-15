from portail import budgets, config, erp, stockage


class Forbidden(Exception):
    pass


def _check_access(user: dict) -> None:
    if config.ALLOWED_GROUP not in user.get("groups", []):
        raise Forbidden(f"{user.get('login')} is not in the group {config.ALLOWED_GROUP}")


def order_page(user: dict, number: str) -> dict:
    _check_access(user)
    order = stockage.load_order(number) or erp.get_order(number)
    contacts = stockage.load_contacts()
    contact = contacts.get(order["supplier_id"])
    if contact is None:
        contact = erp.get_supplier(order["supplier_id"])
        stockage.save_contact(contact)
    budget = budgets.remaining(order["cost_centre"])
    return {
        "order": order,
        "supplier": {
            "company": contact["company"],
            "name": contact["contact_name"],
            "email": contact["contact_email"],
            "phone": contact["contact_phone"],
        },
        "budget": budget if budget is not None else "unavailable",
    }


def orders_list(user: dict, since: str) -> list[dict]:
    _check_access(user)
    erp.sync_orders(since)
    return erp.list_orders(since)
