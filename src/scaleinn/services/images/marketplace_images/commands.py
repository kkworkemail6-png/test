"""Marketplace Images CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("marketplace_images")


@click.group(
    "marketplace-images",
    short_help="Manage marketplace images.",
    help="Manage marketplace images.",
    epilog="No API commands are available yet for this service.",
)
def marketplace_images() -> None:
    log.info("Initializing Marketplace Images module")


# Add commands below, e.g.:
#
#   @marketplace_images.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
