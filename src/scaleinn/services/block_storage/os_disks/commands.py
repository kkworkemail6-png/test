"""OS Disks CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("os_disks")


@click.group(
    "os-disks",
    short_help="Manage OS disks.",
    help="Manage OS disks.",
    epilog="No API commands are available yet for this service.",
)
def os_disks() -> None:
    log.info("Initializing OS Disks module")


# Add commands below, e.g.:
#
#   @os_disks.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
