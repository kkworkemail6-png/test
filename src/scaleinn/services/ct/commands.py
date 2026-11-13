"""CT CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger
from scaleinn.core.output import output_option, render
from scaleinn.core.session import Session, pass_session
from scaleinn.services.ct import operations

log = get_logger("ct")


@click.group("ct", help="Manage CTs (Linux Containers).")
def ct() -> None:
    log.info("Initializing CT module")


@ct.command("list", help="List the CTs in the selected project.")
@output_option
@pass_session
def list_cts(session: Session, output: str | None) -> None:
    data = operations.list_cts(session)
    render(data, output or session.default_output)
    log.info("Command completed")
