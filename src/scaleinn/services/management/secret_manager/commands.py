"""Secret Manager CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("secret_manager")


@click.group(
    "secret-manager",
    short_help="Manage secrets.",
    help="Manage secrets.",
    epilog="No API commands are available yet for this service.",
)
def secret_manager() -> None:
    log.info("Initializing Secret Manager module")


# Add commands below, e.g.:
#
#   @secret_manager.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
