"""Snapshot CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("snapshot")


@click.group(
    "snapshot",
    short_help="Manage snapshots.",
    help="Manage snapshots.",
    epilog="No API commands are available yet for this service.",
)
def snapshot() -> None:
    log.info("Initializing Snapshot module")


# Add commands below, e.g.:
#
#   @snapshot.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
