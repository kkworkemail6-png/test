"""Root user login: username + password.

PLACEHOLDER - the real endpoint and payload will be supplied separately. Until
then the endpoint must be configured in ``~/.scaleinn/config.json``::

    "endpoints": {"root_login": "/api/v1/..."}

and the payload field names below are provisional. Nothing else in the code base
depends on them.
"""

from __future__ import annotations

from typing import Any

ENDPOINT_KEY = "root_login"
DEFAULT_ENDPOINT: str | None = None  # TODO: set once the API contract is supplied
IDENTIFIER_LABEL = "Username"


def build_payload(username: str, password: str) -> dict[str, Any]:
    # TODO: confirm field names against the real contract.
    return {"username": username, "password": password}
