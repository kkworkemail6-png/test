"""WAF CLI commands (argument handling only; logic is in operations.py)."""

from __future__ import annotations

import click

from scaleinn.core.logger import get_logger

log = get_logger("waf")


@click.group(
    "waf",
    short_help="Manage Web Application Firewalls (WAF).",
    help="Manage Web Application Firewalls (WAF).",
    epilog="No API commands are available yet for this service.",
)
def waf() -> None:
    log.info("Initializing WAF module")


# Add commands below, e.g.:
#
#   @waf.command("list", help="List ...")
#   @output_option
#   @pass_session
#   def list_items(session, output):
#       render(operations.list_items(session), output or session.default_output)
#
# See services/ct/commands.py for a complete example, and remove the epilog above
# once the first command exists.
