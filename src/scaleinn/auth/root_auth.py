"""Root user login: username + password.

Backend contract::

    POST {api_url}/api/v1/orca/user/login
    {"usernameOrEmail": "<username>", "password": "<password>"}

The login endpoint is shared with IAM users (see :mod:`scaleinn.auth.iam_auth`),
which send their e-mail address in the same ``usernameOrEmail`` field. The path can
be overridden with ``endpoints.root_login`` in ``~/.scaleinn/config.json``.
"""

from __future__ import annotations

from typing import Any

ENDPOINT_KEY = "root_login"
DEFAULT_ENDPOINT: str | None = "/api/v1/orca/user/login"
IDENTIFIER_LABEL = "Username"


def build_payload(username: str, password: str) -> dict[str, Any]:
    return {"usernameOrEmail": username, "password": password}
