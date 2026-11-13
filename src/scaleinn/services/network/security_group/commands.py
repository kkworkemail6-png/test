"""Security Group CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("security_group")


@click.group(
    "security-group",
    short_help="Manage security groups.",
    help="Manage security groups.",
    epilog="No API commands are available yet for this service.",
)
def security_group() -> None:
    log.info("Initializing Security Group module")


# Add commands below, e.g.:
#
#   @security_group.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
