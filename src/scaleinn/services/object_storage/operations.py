"""All Object Storage backend API operations live in this single file.

Add new operations (create_bucket, delete_bucket, describe_bucket, ...) below as
plain functions with the signature ``operation(session, ...)``. Each one builds a
request and sends it through ``session.client`` - this module never deals with
authentication, HTTP sessions or project selection itself.
"""

from __future__ import annotations

from typing import Any

from scaleinn.core.logger import get_logger
from scaleinn.core.session import Session
from scaleinn.services.object_storage.models import normalize_search

log = get_logger("object_storage")

BUCKET_LIST_PATH = "/api/v1/object-storage/bucket/get-all-bucket"


def list_buckets(session: Session, search: str | None = None) -> Any:
    """GET get-all-bucket for the selected project; returns the parsed JSON body."""
    params = {
        "projectId": session.project_id,
        "search": normalize_search(search),
    }
    log.info("Calling get-all-bucket API")
    # Object Storage is served from its own URL (objectStorageUrl in core/env.py).
    return session.client.get(BUCKET_LIST_PATH, params=params, service="object_storage")
