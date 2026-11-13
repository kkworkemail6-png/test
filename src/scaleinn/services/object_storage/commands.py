"""Object Storage CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger
from scaleinn.core.output import output_option, render
from scaleinn.core.session import Session, pass_session
from scaleinn.services.object_storage import operations

log = get_logger("object_storage")


@click.group("object-storage", help="Manage Object Storage buckets.")
def object_storage() -> None:
    log.info("Initializing Object Storage module")


@object_storage.command("list-buckets", help="List the buckets in the selected project.")
@click.option("--search", default=None, help="Only list buckets matching this text.")
@output_option
@pass_session
def list_buckets(session: Session, search: str | None, output: str | None) -> None:
    data = operations.list_buckets(session, search)
    render(data, output or session.default_output)
    log.info("Command completed")
