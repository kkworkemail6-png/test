"""Local configuration (``~/.scaleinn/config.json``).

Only non-secret settings live here. Tokens are kept separately in
``credentials.json`` (see :mod:`scaleinn.core.credentials`).

Backend URLs come from :mod:`scaleinn.core.env`. ``protocol`` (``https`` or
``http``) selects which environment block is used, and ``api_url`` /
``object_storage_url`` are optional per-machine overrides (``null`` = use the
environment value).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from scaleinn.core import env
from scaleinn.core.exceptions import ConfigurationError
from scaleinn.utils.file_utils import atomic_write_json, ensure_private_dir, read_json

CONFIG_DIR_ENV = "SCALEINN_CONFIG_DIR"
VALID_OUTPUTS = ("table", "json")

DEFAULT_CONFIG: dict[str, Any] = {
    "protocol": env.DEFAULT_PROTOCOL,
    "api_url": None,
    "object_storage_url": None,
    "auth_type": None,
    "project_id": None,
    "project_name": None,
    "default_output": "table",
    "verify_ssl": True,
}

# service name -> (config.json override key, env.py key).
# Pass ``service="<name>"`` to the API client; modules without a URL of their own
# use the default service.
SERVICES: dict[str, tuple[str, str]] = {
    "api": ("api_url", "apiUrl"),
    "object_storage": ("object_storage_url", "objectStorageUrl"),
}
DEFAULT_SERVICE = "api"

# Optional keys that are only present if the user adds them:
#   "ca_bundle": "/path/to/ca.pem"         custom CA certificate bundle
#   "timeout":   30                        read timeout in seconds
#   "endpoints": {"root_login": "/...", "iam_login": "/...", "refresh": "/..."}
#                                           optional path overrides; "refresh" has
#                                           no built-in default because its API
#                                           contract has not been supplied


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
            f"Invalid URL: {url!r}.",
            hint="Use a full URL such as https://app.scaleinn.in:8443 or http://192.168.1.10:8080.",
        )
    return url.rstrip("/")


def protocol_of(url: str) -> str:
    return urlparse(url).scheme


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """Merge defaults and resolve every service URL (override, else environment)."""
    cfg = {**DEFAULT_CONFIG, **raw}
    protocol = cfg["protocol"]
    if protocol not in env.ENVIRONMENTS:
        raise ConfigurationError(
            f"Invalid protocol {protocol!r} in config.json.",
            hint=f"Use one of: {', '.join(env.ENVIRONMENTS)}.",
        )
    for config_key, env_key in SERVICES.values():
        override = cfg.get(config_key)
        cfg[config_key] = validate_api_url(override) if override else env.get_value(protocol, env_key)
    cfg["verify_ssl"] = bool(cfg["verify_ssl"])
    if cfg["default_output"] not in VALID_OUTPUTS:
        raise ConfigurationError(
            f"Invalid default_output {cfg['default_output']!r} in config.json.",
            hint=f"Use one of: {', '.join(VALID_OUTPUTS)}.",
        )
    return cfg


# ------------------------------------------------------------- load / save
def load_config() -> dict[str, Any]:
    """Load configuration with every service URL resolved."""
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
    preserved, and URLs that come from the environment are *not* written into the
    file (only explicit overrides are), so changing ``env.py`` takes effect
    everywhere. Returns the resulting normalized configuration.
    """
    raw = read_json(config_path(), {})
    if not isinstance(raw, dict):
        raise ConfigurationError(f"{config_path()} must contain a JSON object.")
    merged = {**DEFAULT_CONFIG, **raw, **changes}
    normalized = _normalize(merged)
    for config_key, _ in SERVICES.values():
        if merged.get(config_key):  # keep a (cleaned) override; leave "no override" as null
            merged[config_key] = normalized[config_key]
    save_config(merged)
    return normalized


# ----------------------------------------------------------------- helpers
def service_url(config: dict[str, Any], service: str = DEFAULT_SERVICE) -> str:
    """Base URL of a backend service (``"api"`` or ``"object_storage"``)."""
    try:
        config_key, _ = SERVICES[service]
    except KeyError:
        raise ConfigurationError(
            f"Unknown service {service!r}.", hint=f"Known services: {', '.join(SERVICES)}."
        ) from None
    return config[config_key]


def get_endpoint(config: dict[str, Any], name: str, default: str | None = None) -> str | None:
    """Return the configured path override for backend endpoint ``name`` (or ``default``)."""
    endpoints = config.get("endpoints") or {}
    value = endpoints.get(name)
    if not value:
        return default
    if not isinstance(value, str):
        raise ConfigurationError(f"endpoints.{name} in config.json must be a string path.")
    return value if value.startswith("/") else "/" + value


def connection_warnings(config: dict[str, Any]) -> list[str]:
    """Security warnings that apply to the service URLs currently in use."""
    schemes = {protocol_of(service_url(config, name)) for name in SERVICES}
    warnings = []
    if "http" in schemes:
        warnings.append(
            "The API endpoint uses plain HTTP: authentication tokens and data are sent "
            "without TLS encryption. Use HTTPS in production."
        )
    if "https" in schemes and not config["verify_ssl"]:
        warnings.append(
            "SSL certificate verification is disabled. Only do this in controlled "
            "development/testing environments."
        )
    return warnings
