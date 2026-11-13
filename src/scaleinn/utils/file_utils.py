"""Filesystem helpers: private directories and atomic JSON writes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from scaleinn.core.exceptions import ConfigurationError


def ensure_private_dir(path: Path, mode: int = 0o700) -> Path:
    """Create ``path`` (and parents) and force its permissions to ``mode``.

    ``os.makedirs(mode=...)`` is subject to the umask, so an explicit chmod is
    applied afterwards.
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, mode)
    except PermissionError:  # directory owned by someone else; leave as-is
        pass
    return path


def atomic_write_json(path: Path, data: Any, mode: int = 0o600) -> None:
    """Write ``data`` as JSON to ``path`` atomically.

    The content is written to a temporary file in the same directory (created
    with 0600 permissions), fsynced, given its final permissions and then moved
    over the destination with ``os.replace`` so readers never see a partial file.
    """
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=4)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def read_json(path: Path, default: Any = None) -> Any:
    """Read JSON from ``path``; return ``default`` if the file does not exist."""
    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            f"{path} is not valid JSON ({exc.msg} at line {exc.lineno}).",
            hint="Fix or delete the file, then run 'scaleinn configure'.",
        ) from exc
