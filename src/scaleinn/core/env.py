"""Environment settings: the base URLs of the Scaleinn backend services.

This is the Python counterpart of an ``environment.ts`` file. There is one
settings block per protocol, and the ``protocol`` value in ``config.json``
(``https`` by default) selects which block is used. Keys keep the camelCase names
of the web application's environment file so the two are easy to compare.

Each backend service has its own base URL:

    apiUrl            login, projects, organisations, policies, CT and every
                      other module that has no URL of its own
    objectStorageUrl  Object Storage

A single URL can be overridden for one machine in ``config.json``
(``api_url`` / ``object_storage_url``, or ``scaleinn configure --api-url ...``).

To add a service, add its key to both blocks below and register it in
``SERVICES`` in :mod:`scaleinn.core.config`.
"""

from __future__ import annotations

from typing import Any

# Optional value for APIs that will be integrated later (same in both blocks).
BACKUP_OPTION_VALUE = "backup-store"

HTTPS: dict[str, str] = {
    "apiUrl": "https://app.scaleinn.in:8443",
    "objectStorageUrl": "https://app.scaleinn.in:8086",
    "backupOptionValue": BACKUP_OPTION_VALUE,
}

# PLACEHOLDER: the HTTP host/ports were not supplied; this is the example HTTP
# endpoint from the project requirements. Replace with the real HTTP URLs.
HTTP: dict[str, str] = {
    "apiUrl": "http://192.168.192.234:8080",
    "objectStorageUrl": "http://192.168.192.234:8080",
    "backupOptionValue": BACKUP_OPTION_VALUE,
}

ENVIRONMENTS: dict[str, dict[str, str]] = {"https": HTTPS, "http": HTTP}
DEFAULT_PROTOCOL = "https"


def get_environment(protocol: str) -> dict[str, str]:
    """Return a copy of the settings block for ``protocol`` (``"http"`` / ``"https"``)."""
    return dict(ENVIRONMENTS[protocol])


def get_value(protocol: str, key: str, default: Any = None) -> Any:
    """Return one setting of the ``protocol`` block, e.g. ``"backupOptionValue"``."""
    return ENVIRONMENTS[protocol].get(key, default)
