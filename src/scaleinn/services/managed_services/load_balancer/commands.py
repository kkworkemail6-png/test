"""Load Balancer CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("load_balancer")


@click.group(
    "load-balancer",
    short_help="Manage load balancers.",
    help="Manage load balancers.",
    epilog="No API commands are available yet for this service.",
)
def load_balancer() -> None:
    log.info("Initializing Load Balancer module")


# Add commands below, e.g.:
#
#   @load_balancer.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
