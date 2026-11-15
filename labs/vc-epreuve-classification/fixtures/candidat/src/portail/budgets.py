from urllib.error import URLError

from portail import config
from portail.http import get_json


def remaining(cost_centre: str) -> dict | None:
    try:
        line = get_json(
            config.SOURCES["budgets-finance"],
            f"/cost-centres/{cost_centre}/remaining",
            config.BUDGETS_TOKEN_ENV,
            config.TIMEOUT_S,
        )
    except (URLError, TimeoutError):
        return None
    return {"cost_centre": cost_centre, "remaining_eur": line.get("remaining")}
