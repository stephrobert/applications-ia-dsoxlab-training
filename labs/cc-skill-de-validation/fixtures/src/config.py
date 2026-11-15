"""Settings of the portail-achats module, read from the environment."""

import os

DATABASE_URL = os.environ.get("PORTAIL_DATABASE_URL", "sqlite:///portail.db")
PAYMENT_API_KEY = os.environ.get("PORTAIL_PAYMENT_API_KEY", "")
