"""IAM user login: Login ID (registered e-mail address) + password.

Uses the same backend endpoint and payload shape as root login
(:mod:`scaleinn.auth.root_auth`); the e-mail address goes into ``usernameOrEmail``.
The path can be overridden with ``endpoints.iam_login`` in ``config.json``.

NOTE: if the backend later needs an explicit root/IAM discriminator (a separate
endpoint or an extra payload field), this is the one place to add it.
"""

from __future__ import annotations

from typing import Any

ENDPOINT_KEY = "iam_login"
DEFAULT_ENDPOINT: str | None = "/api/v1/orca/user/login"
IDENTIFIER_LABEL = "Login ID (email address)"


def build_payload(login_id: str, password: str) -> dict[str, Any]:
    return {"usernameOrEmail": login_id, "password": password}
