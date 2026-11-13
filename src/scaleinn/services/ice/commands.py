"""ICE CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("ice")


@click.group(
    "ice",
    short_help="Manage ICE virtual machines (VM).",
    help="Manage ICE virtual machines (VM).",
    epilog="No API commands are available yet for this service.",
)
def ice() -> None:
    log.info("Initializing ICE module")


# Add commands below, e.g.:
#
#   @ice.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
