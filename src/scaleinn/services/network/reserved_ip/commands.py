"""Reserved IP CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("reserved_ip")


@click.group(
    "reserved-ip",
    short_help="Manage reserved IP addresses.",
    help="Manage reserved IP addresses.",
    epilog="No API commands are available yet for this service.",
)
def reserved_ip() -> None:
    log.info("Initializing Reserved IP module")


# Add commands below, e.g.:
#
#   @reserved_ip.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
