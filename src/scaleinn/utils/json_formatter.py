"""JSON output formatting."""

from __future__ import annotations

import json
from typing import Any


def format_json(data: Any) -> str:
    """Pretty-print ``data`` as JSON (UTF-8 friendly, stable key order)."""
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)
