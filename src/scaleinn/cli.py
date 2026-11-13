"""Root command group: global options, error handling and command registration."""

from __future__ import annotations

import click

from scaleinn.commands.configure import configure
from scaleinn.commands.version import version, version_string
from scaleinn.core.exceptions import ScaleinnError
from scaleinn.core.logger import get_logger, setup_logging
from scaleinn.core.session import Session
from scaleinn.services import register_services
from scaleinn.utils import terminal

log = get_logger("cli")


class ScaleinnGroup(click.Group):
    """Turns :class:`ScaleinnError` into a clean message and a stable exit code."""

    def invoke(self, ctx: click.Context):
        try:
            return super().invoke(ctx)
        except ScaleinnError as exc:
            log.error("%s: %s", type(exc).__name__, exc.message)
            terminal.error(exc.message, exc.hint)
            ctx.exit(exc.exit_code)


def _print_version(ctx: click.Context, _param: click.Parameter, value: bool) -> None:
    if not value or ctx.resilient_parsing:
        return
    click.echo(version_string())
    ctx.exit()


@click.group(
    cls=ScaleinnGroup,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Scaleinn CLI - manage your Scaleinn cloud resources from the terminal.",
)
@click.option(
    "--version",
    is_flag=True,
    callback=_print_version,
    expose_value=False,
    is_eager=True,
    help="Show the version and exit.",
)
@click.option("--debug", is_flag=True, help="Print debug logs to stderr (secrets are always redacted).")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    setup_logging(debug)
    ctx.obj = Session(debug=debug)
    log.info("CLI initialized")


cli.add_command(configure)
cli.add_command(version)
register_services(cli)
