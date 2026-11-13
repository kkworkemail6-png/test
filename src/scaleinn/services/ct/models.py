"""CT data structures and input validation.

No response model is defined on purpose: the CT list response schema has not been
confirmed yet. Add dataclasses here once it is.
"""

from __future__ import annotations

from scaleinn.core.exceptions import ValidationError

MAX_TEXT_LENGTH = 255
SORT_DIRECTIONS = ("ASC", "DESC")
DEFAULT_SORT_BY = "createdDate"
DEFAULT_SORT_DIRECTION = "DESC"
DEFAULT_PAGE = 0
DEFAULT_PAGE_SIZE = 100


def _clean(value: str | None, option: str) -> str:
    cleaned = (value or "").strip()
    if len(cleaned) > MAX_TEXT_LENGTH:
        raise ValidationError(f"{option} must be at most {MAX_TEXT_LENGTH} characters.")
    if any(ord(ch) < 32 for ch in cleaned):
        raise ValidationError(f"{option} must not contain control characters.")
    return cleaned


def normalize_search(search: str | None) -> str:
    """Validate the optional ``--search`` term (``""`` if absent)."""
    return _clean(search, "--search")


def normalize_sort_by(sort_by: str | None) -> str:
    """Validate ``--sort-by`` (falls back to the default if empty)."""
    return _clean(sort_by, "--sort-by") or DEFAULT_SORT_BY


def normalize_sort_direction(direction: str | None) -> str:
    value = (direction or DEFAULT_SORT_DIRECTION).strip().upper()
    if value not in SORT_DIRECTIONS:
        raise ValidationError(f"--sort-direction must be one of: {', '.join(SORT_DIRECTIONS)}.")
    return value


def validate_paging(page: int, size: int) -> tuple[int, int]:
    if page < 0:
        raise ValidationError("--page must be 0 or greater.")
    if size < 1:
        raise ValidationError("--size must be 1 or greater.")
    return page, size
