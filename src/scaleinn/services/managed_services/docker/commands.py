"""Docker as a Service CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("docker")


@click.group(
    "docker",
    short_help="Manage Docker as a Service.",
    help="Manage Docker as a Service.",
    epilog="No API commands are available yet for this service.",
)
def docker() -> None:
    log.info("Initializing Docker as a Service module")


# Add commands below, e.g.:
#
#   @docker.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
