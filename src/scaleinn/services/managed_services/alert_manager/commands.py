"""Alert Manager CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("alert_manager")


@click.group(
    "alert-manager",
    short_help="Manage Alert Manager.",
    help="Manage Alert Manager.",
    epilog="No API commands are available yet for this service.",
)
def alert_manager() -> None:
    log.info("Initializing Alert Manager module")


# Add commands below, e.g.:
#
#   @alert_manager.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
