"""Object Storage data structures and input validation.

No response model is defined on purpose: the backend response schema has not been
confirmed yet. Add dataclasses here once it is.
"""

from __future__ import annotations

from scaleinn.core.exceptions import ValidationError

MAX_SEARCH_LENGTH = 255


def normalize_search(search: str | None) -> str:
    """Validate and normalize the optional ``--search`` term (``""`` if absent)."""
    if search is None:
        return ""
    cleaned = search.strip()
    if len(cleaned) > MAX_SEARCH_LENGTH:
        raise ValidationError(f"--search must be at most {MAX_SEARCH_LENGTH} characters.")
    if any(ord(ch) < 32 for ch in cleaned):
        raise ValidationError("--search must not contain control characters.")
    return cleaned
