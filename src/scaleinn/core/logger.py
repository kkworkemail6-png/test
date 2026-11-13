"""Logging setup with secret redaction.

Logs go to ``~/.scaleinn/logs/scaleinn.log`` (always, INFO level) and, with
``--debug``, also to stderr at DEBUG level. Every line passes through
:func:`sanitize`, which masks bearer tokens, token/password fields and any value
registered through :func:`register_secret`.
"""

from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler

from scaleinn.core import config as cfg
from scaleinn.utils.file_utils import ensure_private_dir

ROOT_LOGGER = "scaleinn"
REDACTED = "***REDACTED***"
LOG_FORMAT = "%(asctime)s %(levelname)-5s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_SECRET_KEYS = (
    r"access[_-]?token|refresh[_-]?token|id[_-]?token|accessToken|refreshToken|token|"
    r"password|passwd|secret|authorization|api[_-]?key"
)
_BEARER = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/=]+")
_QUOTED = re.compile(rf"(?i)([\"']?(?:{_SECRET_KEYS})[\"']?\s*[:=]\s*)([\"'])(.*?)\2")
_UNQUOTED = re.compile(rf"(?i)((?:{_SECRET_KEYS})[\"']?\s*[:=]\s*[\"']?)([^\s,\"'}}&]+)")

_secrets: set[str] = set()


def register_secret(value: str | None) -> None:
    """Make sure ``value`` is masked wherever it appears in log output."""
    if value and len(value) >= 4:
        _secrets.add(value)


def clear_secrets() -> None:
    _secrets.clear()


def sanitize(text: str) -> str:
    """Mask credentials in ``text``."""
    text = _BEARER.sub(r"\1" + REDACTED, text)
    text = _QUOTED.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}{m.group(2)}", text)
    text = _UNQUOTED.sub(lambda m: f"{m.group(1)}{REDACTED}", text)
    for secret in sorted(_secrets, key=len, reverse=True):
        text = text.replace(secret, REDACTED)
    return text


class SanitizingFormatter(logging.Formatter):
    """Formatter that redacts secrets from the final rendered record
    (including tracebacks)."""

    def format(self, record: logging.LogRecord) -> str:
        return sanitize(super().format(record))


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger(f"{ROOT_LOGGER}.{name}" if name else ROOT_LOGGER)


def setup_logging(debug: bool = False) -> logging.Logger:
    """(Re)configure the ``scaleinn`` logger. Safe to call repeatedly."""
    logger = logging.getLogger(ROOT_LOGGER)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False

    formatter = SanitizingFormatter(LOG_FORMAT, DATE_FORMAT)

    try:
        cfg.ensure_config_dir()
        ensure_private_dir(cfg.log_dir(), 0o700)
        file_handler = RotatingFileHandler(
            cfg.log_path(), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        logger.addHandler(file_handler)
        try:
            cfg.log_path().chmod(0o600)
        except OSError:
            pass
    except OSError:
        # Unwritable home directory etc.: never fail the command because of logging.
        logger.addHandler(logging.NullHandler())

    if debug:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        console.setLevel(logging.DEBUG)
        logger.addHandler(console)

    return logger
