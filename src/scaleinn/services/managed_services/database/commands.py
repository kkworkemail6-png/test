"""Database as a Service CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("database")


@click.group(
    "database",
    short_help="Manage Database as a Service (DBaaS).",
    help="Manage Database as a Service (DBaaS).",
    epilog="No API commands are available yet for this service.",
)
def database() -> None:
    log.info("Initializing Database as a Service module")


# Add commands below, e.g.:
#
#   @database.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
