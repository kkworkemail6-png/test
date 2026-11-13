"""Consistent output rendering for all commands."""

from __future__ import annotations

from typing import Any

import click

from scaleinn.core.config import VALID_OUTPUTS
from scaleinn.utils import terminal
from scaleinn.utils.json_formatter import format_json
from scaleinn.utils.table_formatter import extract_rows, format_table


def output_option(func):
    """Add ``--output json|table`` to a command (default comes from config)."""
    return click.option(
        "--output",
        "-o",
        "output",
        type=click.Choice(list(VALID_OUTPUTS)),
        default=None,
        help="Output format. Defaults to the 'default_output' setting (table).",
    )(func)


def render(data: Any, fmt: str, columns: list[str] | None = None) -> None:
    """Print ``data`` as JSON or as a table.

    Table output needs a list of records. If the response structure is not
    recognizable (the backend schemas are still being confirmed) the raw JSON
    is shown instead, together with a note on stderr.
    """
    if fmt == "json":
        click.echo(format_json(data))
        return

    if data is None:
        click.echo("No data returned.")
        return

    rows = extract_rows(data)
    if rows is None:
        terminal.warn("Response structure is not mapped to a table yet; showing JSON.")
        click.echo(format_json(data))
        return
    if not rows:
        click.echo("No results found.")
        return
    click.echo(format_table(rows, columns))
