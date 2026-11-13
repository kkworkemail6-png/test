"""All CT (Linux Containers) backend API operations live in this single file.

Add further operations (create, delete, describe, start, stop, ...) here.
"""

from __future__ import annotations

from typing import Any

from scaleinn.core import config as cfg
from scaleinn.core.exceptions import EndpointNotConfiguredError
from scaleinn.core.logger import get_logger
from scaleinn.core.session import Session

log = get_logger("ct")

CT_LIST_ENDPOINT_KEY = "ct_list"


def list_cts(session: Session) -> Any:
    """List CTs in the selected project.

    PLACEHOLDER: the endpoint is not known yet, so it is read from
    ``config.json -> endpoints.ct_list``. Replace this with a constant path once
    the API contract is supplied. The ``projectId`` query parameter follows the
    pattern of the Object Storage API but is *provisional* - confirm it.
    """
    endpoint = cfg.get_endpoint(session.config, CT_LIST_ENDPOINT_KEY)
    if not endpoint:
        raise EndpointNotConfiguredError(
            "The CT list endpoint is not configured yet (API contract pending).",
            hint="Set endpoints.ct_list in ~/.scaleinn/config.json once the endpoint is available.",
        )
    log.info("Calling CT list API")
    return session.client.get(endpoint, params={"projectId": session.project_id})
