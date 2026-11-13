"""ASCII table formatting.

The helpers here are deliberately schema-agnostic: the backend response
structures are not finalized yet, so nothing in this module assumes specific
field names. Once a response schema is confirmed, a service can pass an explicit
``columns`` list to :func:`format_table`.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Sequence

MAX_CELL_WIDTH = 60


def extract_rows(data: Any) -> list[dict] | None:
    """Find a list of records in a response, without assuming field names.

    Returns:
        * the list itself if ``data`` is a list of dicts;
        * the only list-of-dicts value if ``data`` is a dict with exactly one;
        * ``None`` if no unambiguous list of records can be found (the caller
          should then fall back to JSON output).
    """
    if isinstance(data, list):
        return data if all(isinstance(item, dict) for item in data) else None
    if isinstance(data, dict):
        candidates = [
            value
            for value in data.values()
            if isinstance(value, list) and value and all(isinstance(i, dict) for i in value)
        ]
        if len(candidates) == 1:
            return candidates[0]
    return None


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)
    else:
        text = str(value)
    text = text.replace("\n", " ")
    if len(text) > MAX_CELL_WIDTH:
        text = text[: MAX_CELL_WIDTH - 3] + "..."
    return text


def format_table(rows: Iterable[dict], columns: Sequence[str] | None = None) -> str:
    """Render ``rows`` (dicts) as an ASCII grid table.

    Args:
        rows: Records to display.
        columns: Column keys in display order. If omitted, the union of all
            keys, in first-seen order, is used.
    """
    rows = list(rows)
    if columns is None:
        columns = []
        for row in rows:
            for key in row:
                if key not in columns:
                    columns.append(key)
    return format_grid([list(columns)] + [[row.get(col) for col in columns] for row in rows])


def format_grid(matrix: Sequence[Sequence[Any]]) -> str:
    """Render a matrix whose first row is the header."""
    text = [[_cell(value) for value in row] for row in matrix]
    widths = [max(len(row[i]) for row in text) for i in range(len(text[0]))]
    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def line(row: Sequence[str]) -> str:
        return "| " + " | ".join(cell.ljust(w) for cell, w in zip(row, widths)) + " |"

    out = [border, line(text[0]), border]
    out.extend(line(row) for row in text[1:])
    out.append(border)
    return "\n".join(out)
