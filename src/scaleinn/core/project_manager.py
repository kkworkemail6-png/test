"""Centralized project selection.

Resource modules never read or write the selected project themselves; they call
``session.project_id`` which delegates here. The stored project ID is only a
convenience: the backend validates project access on every request.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import click

from scaleinn.auth import operations as auth_operations
from scaleinn.core import config as cfg
from scaleinn.core.api_client import ApiClient
from scaleinn.core.exceptions import ProjectNotSelectedError, ResponseFormatError
from scaleinn.core.logger import get_logger
from scaleinn.utils.table_formatter import extract_rows, format_grid

log = get_logger("project")

# The projects API response schema has not been confirmed: these are tolerant
# guesses at the field names. Adjust them once the real schema is known.
_ID_KEYS = ("projectId", "project_id", "id")
_NAME_KEYS = ("projectName", "project_name", "name")
_STATUS_KEYS = ("status", "state")


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    status: str | None = None


def _first(raw: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if raw.get(key) not in (None, ""):
            return raw[key]
    return None


def normalize_project(raw: Any) -> Project | None:
    if not isinstance(raw, dict):
        return None
    project_id = _first(raw, _ID_KEYS)
    if project_id is None:
        return None
    name = _first(raw, _NAME_KEYS) or str(project_id)
    status = _first(raw, _STATUS_KEYS)
    return Project(str(project_id), str(name), str(status) if status is not None else None)


def parse_projects(response: Any) -> list[Project]:
    """Turn the projects API response into :class:`Project` objects.

    Accepts a list of records, or one wrapped in an envelope such as
    ``{"data": {"content": [...]}}``. Raises :class:`ResponseFormatError` if no
    list of records can be found.
    """
    items = response if isinstance(response, list) else extract_rows(response)
    if items is None:
        raise ResponseFormatError("Could not find a project list in the backend response.")
    return [p for p in (normalize_project(i) for i in items) if p]


def fetch_projects(client: ApiClient) -> list[Project]:
    """Retrieve the projects the authenticated user can access."""
    log.info("Fetching accessible projects")
    return parse_projects(auth_operations.list_projects(client))


# ------------------------------------------------------------- selection
def render_projects(projects: list[Project]) -> str:
    rows = [["#", "Project Name", "Status", "Project ID"]]
    for index, project in enumerate(projects, start=1):
        rows.append([index, project.name, project.status or "-", project.id])
    return format_grid(rows)


def choose_project(projects: list[Project]) -> Project:
    """Show the project table and ask the user to pick one by number."""
    click.echo(render_projects(projects))
    click.echo()
    index = click.prompt(
        f"Select project [1-{len(projects)}]",
        type=click.IntRange(1, len(projects)),
        default=1 if len(projects) == 1 else None,
    )
    return projects[index - 1]


def prompt_project_manually() -> Project:
    """Fallback when the projects list cannot be read from the backend."""
    project_id = click.prompt("Project ID").strip()
    name = click.prompt("Project name (optional)", default=project_id, show_default=False).strip()
    return Project(project_id, name or project_id)


def save_selected_project(project: Project) -> None:
    """Persist the selection, changing only the two project fields."""
    cfg.update_config(project_id=project.id, project_name=project.name)
    log.info("Project selected: %s", project.id)


def get_selected_project_id(config: dict[str, Any]) -> str:
    project_id = config.get("project_id")
    if not project_id:
        raise ProjectNotSelectedError(
            "No project selected.", hint="Run 'scaleinn configure' to choose a project."
        )
    return str(project_id)
