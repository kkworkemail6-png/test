"""Token storage (``~/.scaleinn/credentials.json``, mode 600).

Passwords are never accepted by this module: only the whitelisted token fields
are persisted.
"""

from __future__ import annotations

from typing import Any

from scaleinn.core import config as cfg
from scaleinn.utils.file_utils import atomic_write_json, read_json

ALLOWED_KEYS = ("access_token", "refresh_token", "token_type", "expires_at")


def load_credentials() -> dict[str, Any] | None:
    """Return stored credentials, or ``None`` if the user has not logged in."""
    data = read_json(cfg.credentials_path(), None)
    if not isinstance(data, dict) or not data.get("access_token"):
        return None
    return data


def save_credentials(record: dict[str, Any]) -> None:
    """Atomically write ``record`` (whitelisted keys only) with mode 600."""
    clean = {key: record[key] for key in ALLOWED_KEYS if record.get(key) is not None}
    cfg.ensure_config_dir()
    atomic_write_json(cfg.credentials_path(), clean, 0o600)


def clear_credentials() -> None:
    try:
        cfg.credentials_path().unlink()
    except FileNotFoundError:
        pass
