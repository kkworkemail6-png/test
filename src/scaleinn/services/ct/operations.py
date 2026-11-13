"""All CT (Linux Containers) backend API operations live in this single file.

Add further operations (create, delete, describe, start, stop, ...) here as plain
functions ``operation(session, ...)`` that send requests through ``session.client``.
"""

from __future__ import annotations

from typing import Any

from scaleinn.core.logger import get_logger
from scaleinn.core.session import Session
from scaleinn.services.ct.models import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT_BY,
    DEFAULT_SORT_DIRECTION,
    normalize_search,
    normalize_sort_by,
    normalize_sort_direction,
    validate_paging,
)

log = get_logger("ct")

CT_LIST_PATH = "/api/v1/orca/compute/lxc/get-list-by-projectid"


def list_cts(
    session: Session,
    search: str | None = None,
    page: int = DEFAULT_PAGE,
    size: int = DEFAULT_PAGE_SIZE,
    sort_by: str = DEFAULT_SORT_BY,
    sort_direction: str = DEFAULT_SORT_DIRECTION,
) -> Any:
    """GET get-list-by-projectid for the selected project; returns the parsed JSON body."""
    page, size = validate_paging(page, size)
    params = {
        "projectId": session.project_id,
        "sortBy": normalize_sort_by(sort_by),
        "sortDirection": normalize_sort_direction(sort_direction),
        "page": page,
        "size": size,
        "search": normalize_search(search),
    }
    log.info("Calling CT list API")
    return session.client.get(CT_LIST_PATH, params=params)
