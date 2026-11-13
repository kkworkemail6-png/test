"""Local configuration (``~/.scaleinn/config.json``).

Only non-secret settings live here. Tokens are kept separately in
``credentials.json`` (see :mod:`scaleinn.core.credentials`).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scaleinn.core.exceptions import ConfigurationError
from scaleinn.utils.file_utils import atomic_write_json, ensure_private_dir, read_json

CONFIG_DIR_ENV = "SCALEINN_CONFIG_DIR"
DEFAULT_API_URL = "https://app.scaleinn.in:8086"
VALID_OUTPUTS = ("table", "json")

DEFAULT_CONFIG: dict[str, Any] = {
    "api_url": DEFAULT_API_URL,
    "protocol": "https",
    "auth_type": None,
    "project_id": None,
    "project_name": None,
    "default_output": "table",
    "verify_ssl": True,
}

# Optional keys that are only present if the user adds them:
#   "ca_bundle": "/path/to/ca.pem"         custom CA certificate bundle
#   "timeout":   30                        read timeout in seconds
#   "endpoints": {"root_login": "/...", "iam_login": "/...", "refresh": "/...",
#                 "projects": "/...", "ct_list": "/..."}
#                                           backend endpoints whose API contract
#                                           has not been supplied yet


# ---------------------------------------------------------------- locations
def config_dir() -> Path:
    override = os.environ.get(CONFIG_DIR_ENV)
    return Path(override).expanduser() if override else Path.home() / ".scaleinn"


def config_path() -> Path:
    return config_dir() / "config.json"


def credentials_path() -> Path:
    return config_dir() / "credentials.json"


def log_dir() -> Path:
    return config_dir() / "logs"


def log_path() -> Path:
    return log_dir() / "scaleinn.log"


def ensure_config_dir() -> Path:
    """Create ``~/.scaleinn`` with mode 700 if needed."""
    return ensure_private_dir(config_dir(), 0o700)


# --------------------------------------------------------------- validation
def validate_api_url(url: str | None) -> str:
    """Return ``url`` without a trailing slash, or raise if it is not http(s)."""
    url = (url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ConfigurationError(
            f"Invalid API URL: {url!r}.",
            hint="Use a full URL such as https://app.scaleinn.in:8086 or http://192.168.1.10:8080.",
        )
    return url.rstrip("/")


def protocol_of(url: str) -> str:
    return urlparse(url).scheme


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    cfg = {**DEFAULT_CONFIG, **raw}
    cfg["api_url"] = validate_api_url(cfg["api_url"])
    cfg["protocol"] = protocol_of(cfg["api_url"])  # always derived from api_url
    cfg["verify_ssl"] = bool(cfg["verify_ssl"])
    if cfg["default_output"] not in VALID_OUTPUTS:
        raise ConfigurationError(
            f"Invalid default_output {cfg['default_output']!r} in config.json.",
            hint=f"Use one of: {', '.join(VALID_OUTPUTS)}.",
        )
    return cfg


# ------------------------------------------------------------- load / save
def load_config() -> dict[str, Any]:
    """Load configuration, filling in defaults for missing keys."""
    raw = read_json(config_path(), {})
    if not isinstance(raw, dict):
        raise ConfigurationError(f"{config_path()} must contain a JSON object.")
    return _normalize(raw)


def save_config(config: dict[str, Any]) -> None:
    ensure_config_dir()
    atomic_write_json(config_path(), config, 0o600)


def update_config(**changes: Any) -> dict[str, Any]:
    """Change only the given keys and keep everything else as it was.

    Unknown keys already present in the file (for example ``endpoints``) are
    preserved. Returns the resulting normalized configuration.
    """
    raw = read_json(config_path(), {})
    if not isinstance(raw, dict):
        raise ConfigurationError(f"{config_path()} must contain a JSON object.")
    merged = {**DEFAULT_CONFIG, **raw, **changes}
    normalized = _normalize(merged)
    merged["api_url"] = normalized["api_url"]
    merged["protocol"] = normalized["protocol"]
    save_config(merged)
    return normalized


# ----------------------------------------------------------------- helpers
def get_endpoint(config: dict[str, Any], name: str, default: str | None = None) -> str | None:
    """Return the configured path for backend endpoint ``name`` (or ``default``).

    Used for endpoints whose API contract is still pending, so they can be
    provided through ``config.json`` without a code change.
    """
    endpoints = config.get("endpoints") or {}
    value = endpoints.get(name)
    if not value:
        return default
    if not isinstance(value, str):
        raise ConfigurationError(f"endpoints.{name} in config.json must be a string path.")
    return value if value.startswith("/") else "/" + value


def connection_warnings(config: dict[str, Any]) -> list[str]:
    """Security warnings that apply to the current connection settings."""
    warnings = []
    if config["protocol"] == "http":
        warnings.append(
            "The API endpoint uses plain HTTP: authentication tokens and data are sent "
            "without TLS encryption. Use HTTPS in production."
        )
    elif not config["verify_ssl"]:
        warnings.append(
            "SSL certificate verification is disabled. Only do this in controlled "
            "development/testing environments."
        )
    return warnings
