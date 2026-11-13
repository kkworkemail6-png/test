"""Login dispatcher: picks root or IAM login and turns the response into tokens."""

from __future__ import annotations

from types import ModuleType
from typing import Any

from scaleinn.auth import iam_auth, root_auth
from scaleinn.core import config as cfg
from scaleinn.core.api_client import ApiClient
from scaleinn.core.exceptions import (
    APIError,
    AuthenticationError,
    EndpointNotConfiguredError,
    ValidationError,
)
from scaleinn.core.logger import get_logger
from scaleinn.core.token_manager import make_token_record

log = get_logger("auth")

AUTH_MODULES: dict[str, ModuleType] = {"root": root_auth, "iam": iam_auth}

# PLACEHOLDER response mapping - adjust when the login response contract is known.
_ACCESS_KEYS = ("access_token", "accessToken", "token")
_REFRESH_KEYS = ("refresh_token", "refreshToken")
_EXPIRES_IN_KEYS = ("expires_in", "expiresIn")
_EXPIRES_AT_KEYS = ("expires_at", "expiresAt")
_TYPE_KEYS = ("token_type", "tokenType")


def _pick(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if data.get(key) not in (None, ""):
            return data[key]
    return None


def parse_token_response(data: Any) -> dict[str, Any]:
    """Convert a login/refresh response into a ``credentials.json`` record.

    The response body is never logged. Raises :class:`APIError` if it contains
    no access token.
    """
    if isinstance(data, dict) and _pick(data, _ACCESS_KEYS) is None and isinstance(data.get("data"), dict):
        data = data["data"]  # tolerate an envelope such as {"data": {...}}
    access = _pick(data, _ACCESS_KEYS) if isinstance(data, dict) else None
    if not access:
        raise APIError("The backend response did not contain an access token.")
    return make_token_record(
        access_token=str(access),
        refresh_token=_pick(data, _REFRESH_KEYS),
        token_type=_pick(data, _TYPE_KEYS),
        expires_in=_pick(data, _EXPIRES_IN_KEYS),
        expires_at=_pick(data, _EXPIRES_AT_KEYS),
    )


def login(client: ApiClient, config: dict[str, Any], auth_type: str, identifier: str, password: str) -> dict[str, Any]:
    """Authenticate and return the token record (nothing is stored here)."""
    module = AUTH_MODULES.get(auth_type)
    if module is None:
        raise ValidationError(f"Unknown authentication type: {auth_type!r}.")

    endpoint = cfg.get_endpoint(config, module.ENDPOINT_KEY, module.DEFAULT_ENDPOINT)
    if not endpoint:
        raise EndpointNotConfiguredError(
            f"The {auth_type} login endpoint is not configured yet (API contract pending).",
            hint=f"Set endpoints.{module.ENDPOINT_KEY} in ~/.scaleinn/config.json, "
            "or use 'scaleinn configure --with-token' to supply an existing bearer token.",
        )

    log.info("Authenticating (%s)", auth_type)
    payload = module.build_payload(identifier, password)
    response = client.post(endpoint, json=payload, auth=False)  # payload is never logged
    record = parse_token_response(response)
    log.info("Authentication successful")
    return record
