from pathlib import Path

SOURCES = {
    "erp-achats": "https://erp-achats.example.invalid/api/v2",
    "budgets-finance": "https://budgets-finance.example.invalid/api",
}

ERP_TOKEN_ENV = "PORTAIL_ERP_TOKEN"
BUDGETS_TOKEN_ENV = "PORTAIL_BUDGETS_TOKEN"

ALLOWED_GROUP = "achats"

DATA_DIR = Path("/var/lib/portail-achats")
ORDERS_DIR = DATA_DIR / "commandes"
CONTACTS_FILE = DATA_DIR / "contacts.json"

TIMEOUT_S = 5
