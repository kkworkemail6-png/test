"""Account-level backend APIs: accessible projects, organisations and user policies.

Like the resource modules, all of these APIs live in this single file; add further
account-level APIs below as plain functions that take the common ``ApiClient``.
They use the default ("api") backend URL from :mod:`scaleinn.core.env`.

The response bodies are returned as parsed JSON; their schemas have not been
confirmed, so nothing here assumes field names.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from scaleinn.core.exceptions import ValidationError
from scaleinn.core.logger import get_logger

if TYPE_CHECKING:  # pragma: no cover
    from scaleinn.core.api_client import ApiClient

log = get_logger("auth")

PROJECTS_PATH = "/api/v1/orca/projects/list"
ORGANIZATIONS_PATH = "/api/v1/orca/organisation/list"
MY_POLICIES_PATH = "/api/v1/orca/policies/my-policies"

DEFAULT_PAGE_SIZE = 100
SORT_DIRECTIONS = ("ASC", "DESC")


def _clean_search(search: str | None) -> str:
    cleaned = (search or "").strip()
    if len(cleaned) > 255 or any(ord(ch) < 32 for ch in cleaned):
        raise ValidationError("The search text is too long or contains control characters.")
    return cleaned


def _check_size(size: int) -> int:
    if size < 1:
        raise ValidationError("size must be 1 or greater.")
    return size


def list_projects(
    client: "ApiClient",
    search: str | None = None,
    size: int = DEFAULT_PAGE_SIZE,
    sort_dir: str = "DESC",
) -> Any:
    """GET the projects the authenticated user can access."""
    direction = (sort_dir or "DESC").strip().upper()
    if direction not in SORT_DIRECTIONS:
        raise ValidationError(f"sort_dir must be one of: {', '.join(SORT_DIRECTIONS)}.")
    params = {"search": _clean_search(search), "size": _check_size(size), "sortDir": direction}
    log.info("Calling projects list API")
    return client.get(PROJECTS_PATH, params=params)


def list_organizations(
    client: "ApiClient", search: str | None = None, size: int = DEFAULT_PAGE_SIZE
) -> Any:
    """GET the organisations the authenticated user can access."""
    params = {"size": _check_size(size), "search": _clean_search(search)}
    log.info("Calling organisation list API")
    return client.get(ORGANIZATIONS_PATH, params=params)


def get_my_policies(client: "ApiClient", project_id: str | None = None) -> Any:
    """GET the authenticated user's policies, for ``project_id`` (empty = no project)."""
    params = {"projectId": (project_id or "").strip()}
    log.info("Calling my-policies API")
    return client.get(MY_POLICIES_PATH, params=params)
