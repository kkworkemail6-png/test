"""Version reporting."""

from __future__ import annotations

import platform

import click

from scaleinn.version import __version__


def version_string() -> str:
    return f"scaleinn-cli/{__version__} Python/{platform.python_version()} {platform.system()}/{platform.release()}"


@click.command("version", help="Show the CLI version.")
def version() -> None:
    click.echo(version_string())
