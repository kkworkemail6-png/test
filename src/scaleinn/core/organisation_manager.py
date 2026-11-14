"""Centralized organisation selection (mirrors :mod:`scaleinn.core.project_manager`).

The selected organisation is stored in ``credentials.json`` together with the token it
belongs to. It is a convenience, not authorization: the backend checks access.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import click

from scaleinn.auth import operations as auth_operations
from scaleinn.core import credentials
from scaleinn.core.api_client import ApiClient
from scaleinn.core.exceptions import ResponseFormatError
from scaleinn.core.logger import get_logger
from scaleinn.utils.table_formatter import extract_rows, format_grid

log = get_logger("organisation")

# The organisation API response schema has not been confirmed: these are tolerant
# guesses at the field names. Adjust them once the real schema is known.
_ID_KEYS = ("organisationId", "organizationId", "orgId", "org_id", "id")
_NAME_KEYS = ("organisationName", "organizationName", "orgName", "org_name", "name")


@dataclass(frozen=True)
class Organisation:
    id: str
    name: str


def _first(raw: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if raw.get(key) not in (None, ""):
            return raw[key]
    return None


def normalize_organisation(raw: Any) -> Organisation | None:
    if not isinstance(raw, dict):
        return None
    org_id = _first(raw, _ID_KEYS)
    if org_id is None:
        return None
    return Organisation(str(org_id), str(_first(raw, _NAME_KEYS) or org_id))


def parse_organisations(response: Any) -> list[Organisation]:
    """Turn the organisation API response into :class:`Organisation` objects.

    Accepts a list of records, or one inside an envelope such as
    ``{"data": {"content": [...]}}``. Raises :class:`ResponseFormatError` if no list
    of records can be found.
    """
    items = response if isinstance(response, list) else extract_rows(response)
    if items is None:
        raise ResponseFormatError("Could not find an organisation list in the backend response.")
    return [o for o in (normalize_organisation(i) for i in items) if o]


def fetch_organisations(client: ApiClient) -> list[Organisation]:
    """Retrieve the organisations the authenticated user can access."""
    log.info("Fetching accessible organisations")
    return parse_organisations(auth_operations.list_organizations(client))


def render_organisations(organisations: list[Organisation]) -> str:
    rows = [["#", "Organisation Name", "Organisation ID"]]
    for index, organisation in enumerate(organisations, start=1):
        rows.append([index, organisation.name, organisation.id])
    return format_grid(rows)


def choose_organisation(organisations: list[Organisation]) -> Organisation:
    """Show the organisations and ask the user to pick one by number."""
    click.echo(render_organisations(organisations))
    click.echo()
    index = click.prompt(
        f"Select organisation [1-{len(organisations)}]",
        type=click.IntRange(1, len(organisations)),
        default=1 if len(organisations) == 1 else None,
    )
    return organisations[index - 1]


def prompt_organisation_manually() -> Organisation | None:
    """Fallback when the list cannot be read: ask for an ID, or ``None`` to skip."""
    org_id = click.prompt("Organisation ID (leave empty to skip)", default="", show_default=False).strip()
    if not org_id:
        return None
    name = click.prompt("Organisation name (optional)", default=org_id, show_default=False).strip()
    return Organisation(org_id, name or org_id)


def save_selected_organisation(organisation: Organisation | None) -> None:
    """Store the selection in ``credentials.json`` (``None`` clears it)."""
    if organisation is None:
        credentials.update_context(organisation=None)
        log.info("No organisation selected")
        return
    credentials.update_context(organisation=credentials.selection(organisation.id, organisation.name))
    log.info("Organisation selected: %s", organisation.id)
