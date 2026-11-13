"""Cloud DNS CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("cloud_dns")


@click.group(
    "cloud-dns",
    short_help="Manage Cloud DNS.",
    help="Manage Cloud DNS.",
    epilog="No API commands are available yet for this service.",
)
def cloud_dns() -> None:
    log.info("Initializing Cloud DNS module")


# Add commands below, e.g.:
#
#   @cloud_dns.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
