"""IAM user login: Login ID (registered e-mail address) + password.

PLACEHOLDER - see :mod:`scaleinn.auth.root_auth`. Configure the endpoint with
``endpoints.iam_login`` in ``~/.scaleinn/config.json`` until the contract exists.
"""

from __future__ import annotations

from typing import Any

ENDPOINT_KEY = "iam_login"
DEFAULT_ENDPOINT: str | None = None  # TODO: set once the API contract is supplied
IDENTIFIER_LABEL = "Login ID (email address)"


def build_payload(login_id: str, password: str) -> dict[str, Any]:
    # TODO: confirm field names against the real contract.
    return {"loginId": login_id, "password": password}
