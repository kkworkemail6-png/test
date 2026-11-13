"""Network Storage CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("network_storage")


@click.group(
    "network-storage",
    short_help="Manage network storage.",
    help="Manage network storage.",
    epilog="No API commands are available yet for this service.",
)
def network_storage() -> None:
    log.info("Initializing Network Storage module")


# Add commands below, e.g.:
#
#   @network_storage.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
