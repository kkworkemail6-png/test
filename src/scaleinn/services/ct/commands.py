"""CT CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger
from scaleinn.core.output import output_option, render
from scaleinn.core.session import Session, pass_session
from scaleinn.services.ct import operations
from scaleinn.services.ct.models import (
    DEFAULT_PAGE,
    DEFAULT_PAGE_SIZE,
    DEFAULT_SORT_BY,
    DEFAULT_SORT_DIRECTION,
    SORT_DIRECTIONS,
)

log = get_logger("ct")


@click.group("ct", help="Manage CTs (Linux Containers).")
def ct() -> None:
    log.info("Initializing CT module")


@ct.command("list", help="List the CTs in the selected project.")
@click.option("--search", default=None, help="Only list CTs matching this text.")
@click.option(
    "--page", type=click.IntRange(min=0), default=DEFAULT_PAGE, show_default=True,
    help="Page number (starts at 0).",
)
@click.option(
    "--size", type=click.IntRange(min=1), default=DEFAULT_PAGE_SIZE, show_default=True,
    help="Number of CTs per page.",
)
@click.option("--sort-by", default=DEFAULT_SORT_BY, show_default=True, help="Field to sort by.")
@click.option(
    "--sort-direction",
    type=click.Choice(SORT_DIRECTIONS, case_sensitive=False),
    default=DEFAULT_SORT_DIRECTION,
    show_default=True,
    help="Sort order.",
)
@output_option
@pass_session
def list_cts(
    session: Session,
    search: str | None,
    page: int,
    size: int,
    sort_by: str,
    sort_direction: str,
    output: str | None,
) -> None:
    data = operations.list_cts(session, search, page, size, sort_by, sort_direction)
    render(data, output or session.default_output)
    log.info("Command completed")
