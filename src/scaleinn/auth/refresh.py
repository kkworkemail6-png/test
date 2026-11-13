"""Token refresh.

PLACEHOLDER - whether the backend supports refresh tokens, and how, is still to
be confirmed. Refresh is considered *unsupported* until ``endpoints.refresh`` is
set in ``~/.scaleinn/config.json``; the CLI then simply asks the user to sign in
again when a token expires.
"""

from __future__ import annotations

from typing import Any

from scaleinn.auth.login import parse_token_response
from scaleinn.core import config as cfg
from scaleinn.core.api_client import ApiClient
from scaleinn.core.exceptions import AuthenticationError

ENDPOINT_KEY = "refresh"
DEFAULT_ENDPOINT: str | None = None  # TODO: set once the API contract is supplied


def refresh_supported(config: dict[str, Any]) -> bool:
    return bool(cfg.get_endpoint(config, ENDPOINT_KEY, DEFAULT_ENDPOINT))


def build_payload(refresh_token: str) -> dict[str, Any]:
    # TODO: confirm field name against the real contract.
    return {"refreshToken": refresh_token}


def refresh_tokens(client: ApiClient, config: dict[str, Any], refresh_token: str) -> dict[str, Any]:
    """Call the refresh endpoint and return the new token record."""
    endpoint = cfg.get_endpoint(config, ENDPOINT_KEY, DEFAULT_ENDPOINT)
    if not endpoint:
        raise AuthenticationError(
            "Token refresh is not available.", hint="Run 'scaleinn configure' to sign in again."
        )
    response = client.post(endpoint, json=build_payload(refresh_token), auth=False)
    return parse_token_response(response)
