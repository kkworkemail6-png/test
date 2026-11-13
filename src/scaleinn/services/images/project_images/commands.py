"""Project Images CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("project_images")


@click.group(
    "project-images",
    short_help="Manage project images.",
    help="Manage project images.",
    epilog="No API commands are available yet for this service.",
)
def project_images() -> None:
    log.info("Initializing Project Images module")


# Add commands below, e.g.:
#
#   @project_images.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
