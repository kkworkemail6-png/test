"""The user's policies: loaded after login / project selection and kept in ``credentials.json``.

The my-policies response schema has not been confirmed, so it is stored exactly as the
backend returned it. The stored copy is informational: the backend enforces policies.
"""

from __future__ import annotations

from typing import Any

from scaleinn.auth import operations as auth_operations
from scaleinn.core import credentials
from scaleinn.core.api_client import ApiClient
from scaleinn.core.exceptions import ScaleinnError
from scaleinn.core.logger import get_logger

log = get_logger("policies")


def refresh_policies(client: ApiClient, project_id: str | None) -> tuple[bool, str | None]:
    """Fetch the user's policies for ``project_id`` and store them.

    Failing to load the policies never aborts ``configure``: the stale copy is removed
    (it may belong to another project) and the reason is returned.

    Returns:
        ``(True, None)`` if the policies were stored, else ``(False, reason)``.
    """
    try:
        policies = auth_operations.get_my_policies(client, project_id)
    except ScaleinnError as exc:
        credentials.update_context(policies=None)
        log.warning("Could not load policies: %s", exc.message)
        return False, exc.message
    credentials.update_context(policies=policies)  # a None/empty body just clears the stored copy
    log.info("Policies stored")
    return True, None


def get_stored_policies() -> Any:
    """The policies saved by the last ``scaleinn configure`` (``None`` if none)."""
    return credentials.get_policies()
