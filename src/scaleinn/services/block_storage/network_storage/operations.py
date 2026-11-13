"""All Network Storage backend API operations live in this single file.

Add operations as plain functions ``operation(session, ...)`` that send requests
through ``session.client``. Use ``session.project_id`` when the API needs a project,
and ``service="..."`` (see ``core/env.py``) if this service has its own backend URL.
See ``services/ct/operations.py`` for a complete example.

No API contract has been supplied for this service yet, so nothing is implemented.
"""

from __future__ import annotations

from scaleinn.core.logger import get_logger

log = get_logger("network_storage")
