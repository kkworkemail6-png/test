"""IPAM CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("ipam")


@click.group(
    "ipam",
    short_help="Manage IP address management (IPAM).",
    help="Manage IP address management (IPAM).",
    epilog="No API commands are available yet for this service.",
)
def ipam() -> None:
    log.info("Initializing IPAM module")


# Add commands below, e.g.:
#
#   @ipam.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
