"""Local auth state (``~/.scaleinn/credentials.json``, mode 600).

One file holds everything that belongs to the logged-in identity:

* the tokens: ``access_token``, ``refresh_token``, ``token_type``, ``expires_at``
* the selection made in ``scaleinn configure``: ``organisation`` and ``project``
  (each ``{"id": ..., "name": ...}``)
* the user's ``policies`` (the my-policies API response for the selected project)

Logging in again replaces the tokens *and* clears the selection and policies, which
``scaleinn configure`` then fills in again for the new login. A token refresh keeps
them. Passwords are never accepted by this module: only whitelisted keys are written.
The stored selection and policies are conveniences, not authorization: the backend
checks access on every request.
"""

from __future__ import annotations

from typing import Any

from scaleinn.core import config as cfg
from scaleinn.core.exceptions import NotConfiguredError
from scaleinn.utils.file_utils import atomic_write_json, read_json

TOKEN_KEYS = ("access_token", "refresh_token", "token_type", "expires_at")
CONTEXT_KEYS = ("organisation", "project", "policies")
ALLOWED_KEYS = TOKEN_KEYS + CONTEXT_KEYS


def load_credentials() -> dict[str, Any] | None:
    """Return the stored record, or ``None`` if the user has not logged in."""
    data = read_json(cfg.credentials_path(), None)
    if not isinstance(data, dict) or not data.get("access_token"):
        return None
    return data


def load_context() -> dict[str, Any]:
    """The stored organisation / project / policies (empty if none or not logged in)."""
    data = load_credentials() or {}
    return {key: data[key] for key in CONTEXT_KEYS if data.get(key) is not None}


def _write(record: dict[str, Any]) -> None:
    clean = {key: record[key] for key in ALLOWED_KEYS if record.get(key) is not None}
    cfg.ensure_config_dir()
    atomic_write_json(cfg.credentials_path(), clean, 0o600)


def save_credentials(record: dict[str, Any], keep_context: bool = False) -> None:
    """Atomically write the tokens in ``record`` with mode 600.

    By default the stored organisation, project and policies are dropped, because a
    new login is a new identity. Pass ``keep_context=True`` (token refresh) to keep them.
    """
    tokens = {key: record[key] for key in TOKEN_KEYS if record.get(key) is not None}
    if keep_context:
        tokens.update(load_context())
    _write(tokens)


def update_context(**changes: Any) -> None:
    """Change organisation / project / policies in the credentials file.

    Tokens and the other context values are kept. A value of ``None`` removes the
    key. Raises :class:`NotConfiguredError` if the user is not logged in.
    """
    unknown = set(changes) - set(CONTEXT_KEYS)
    if unknown:
        raise ValueError(f"Unknown credentials keys: {', '.join(sorted(unknown))}")
    record = load_credentials()
    if record is None:
        raise NotConfiguredError("You are not logged in.", hint="Run 'scaleinn configure' to sign in.")
    updated = dict(record)
    for key, value in changes.items():
        if value is None:
            updated.pop(key, None)
        else:
            updated[key] = value
    _write(updated)


def selection(item_id: str, name: str | None = None) -> dict[str, str]:
    """The ``{"id", "name"}`` shape used for the organisation and project."""
    return {"id": str(item_id), "name": str(name or item_id)}


def get_organisation() -> dict[str, Any] | None:
    return load_context().get("organisation")


def get_project() -> dict[str, Any] | None:
    return load_context().get("project")


def get_policies() -> Any:
    return load_context().get("policies")


def clear_credentials() -> None:
    try:
        cfg.credentials_path().unlink()
    except FileNotFoundError:
        pass
