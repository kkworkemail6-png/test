"""Click group classes that control how ``--help`` lists commands.

* :class:`OrderedGroup` lists sub-commands in the order they were added (Click
  sorts them alphabetically by default). Category groups such as
  ``scaleinn network`` use it so the help follows the product listing.
* :class:`SectionedGroup` additionally prints the commands under titled sections
  (``Compute``, ``Network``, ...). The root ``scaleinn`` command uses it.
"""

from __future__ import annotations

import click


class OrderedGroup(click.Group):
    """A group whose help lists commands in registration order."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        return list(self.commands)


class SectionedGroup(OrderedGroup):
    """A group whose help shows commands under titled sections.

    ``sections`` is a list of ``(title, [command names])``. Commands that are not
    in any section are shown last under ``Commands``.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.sections: list[tuple[str, list[str]]] = []

    def add_section(self, title: str, *commands: click.Command) -> None:
        """Register ``commands`` on this group and list them under ``title``."""
        for command in commands:
            self.add_command(command)
        self.sections.append((title, [command.name for command in commands]))

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        listed: set[str] = set()
        for title, names in self.sections:
            rows = self._rows(ctx, formatter, names)
            listed.update(names)
            if rows:
                with formatter.section(title):
                    formatter.write_dl(rows)

        rest = [name for name in self.list_commands(ctx) if name not in listed]
        rows = self._rows(ctx, formatter, rest)
        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)

    @staticmethod
    def _rows(ctx: click.Context, formatter: click.HelpFormatter, names: list[str]) -> list[tuple[str, str]]:
        rows = []
        for name in names:
            command = ctx.command.get_command(ctx, name)  # type: ignore[attr-defined]
            if command is None or command.hidden:
                continue
            limit = max(formatter.width - 6 - len(name), 45)
            rows.append((name, command.get_short_help_str(limit)))
        return rows
