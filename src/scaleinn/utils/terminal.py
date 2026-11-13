"""Terminal I/O helpers. Messages for humans go to stderr; data goes to stdout."""

from __future__ import annotations

import click


def info(message: str = "") -> None:
    click.echo(message)


def success(message: str) -> None:
    click.echo(click.style(message, fg="green"))


def warn(message: str) -> None:
    click.echo(click.style("WARNING: ", fg="yellow", bold=True) + message, err=True)


_warned: set[str] = set()


def warn_once(message: str) -> None:
    """Like :func:`warn`, but each distinct message is shown once per process."""
    if message not in _warned:
        _warned.add(message)
        warn(message)


def reset_warnings() -> None:
    _warned.clear()


def error(message: str, hint: str | None = None) -> None:
    click.echo(click.style("Error: ", fg="red", bold=True) + message, err=True)
    if hint:
        click.echo(f"Hint: {hint}", err=True)
