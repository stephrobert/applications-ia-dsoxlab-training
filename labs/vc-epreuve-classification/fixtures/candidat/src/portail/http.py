import json
import os
import urllib.request


def get_json(base: str, path: str, token_env: str, timeout: int) -> object:
    request = urllib.request.Request(
        f"{base}{path}",
        method="GET",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {os.environ.get(token_env, '')}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))
