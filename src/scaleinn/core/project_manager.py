"""Centralized project selection.

Resource modules never read or write the selected project themselves; they call
``session.project_id`` which delegates here. The stored project ID is only a
convenience: the backend validates project access on every request.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import click

from scaleinn.core import config as cfg
from scaleinn.core.api_client import ApiClient
from scaleinn.core.exceptions import (
    APIError,
    EndpointNotConfiguredError,
    ProjectNotSelectedError,
)
from scaleinn.core.logger import get_logger
from scaleinn.utils.table_formatter import format_grid

log = get_logger("project")

# ---------------------------------------------------------------------------
# PLACEHOLDER: the "accessible projects" API contract has not been supplied.
# The endpoint comes from config.json -> endpoints.projects, and the field
# names below are a defensive guess to be replaced by the real schema.
# ---------------------------------------------------------------------------
PROJECTS_ENDPOINT_KEY = "projects"
_ID_KEYS = ("projectId", "project_id", "id")
_NAME_KEYS = ("projectName", "project_name", "name")
_STATUS_KEYS = ("status", "state")
_LIST_KEYS = ("projects", "data", "items", "results")


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
    """Turn the projects API response into :class:`Project` objects."""
    items = response
    if isinstance(response, dict):
        items = next((response[k] for k in _LIST_KEYS if isinstance(response.get(k), list)), None)
    if not isinstance(items, list):
        raise APIError("Could not find a project list in the backend response.")
    projects = [p for p in (normalize_project(i) for i in items) if p]
    return projects


def fetch_projects(client: ApiClient, config: dict[str, Any]) -> list[Project]:
    """Retrieve the projects the authenticated user can access."""
    endpoint = cfg.get_endpoint(config, PROJECTS_ENDPOINT_KEY)
    if not endpoint:
        raise EndpointNotConfiguredError(
            "The 'accessible projects' endpoint is not configured yet (API contract pending).",
            hint="Set endpoints.projects in ~/.scaleinn/config.json once it is available.",
        )
    log.info("Fetching accessible projects")
    return parse_projects(client.get(endpoint))


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
    """Fallback while the projects API is not configured."""
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
