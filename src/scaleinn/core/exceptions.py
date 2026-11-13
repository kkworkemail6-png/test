"""Exception hierarchy and process exit codes.

Every error that should be shown to the user as a clean message (instead of a
traceback) derives from :class:`ScaleinnError`. The top-level CLI group catches
it, prints the message (and optional hint) and exits with ``exit_code``.
"""

from __future__ import annotations

# Standard exit codes
EXIT_OK = 0
EXIT_GENERAL = 1
EXIT_USAGE = 2  # reserved: Click uses 2 for bad command-line usage
EXIT_AUTH = 3
EXIT_FORBIDDEN = 4
EXIT_NETWORK = 5
EXIT_CONFIG = 6
EXIT_API = 7


class ScaleinnError(Exception):
    """Base class for all expected CLI errors."""

    exit_code = EXIT_GENERAL

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class ConfigurationError(ScaleinnError):
    """Local configuration is missing or invalid."""

    exit_code = EXIT_CONFIG


class NotConfiguredError(ConfigurationError):
    """The CLI has not been configured / the user has not logged in yet."""


class EndpointNotConfiguredError(ConfigurationError):
    """A backend endpoint whose API contract has not been supplied yet."""


class ProjectNotSelectedError(ConfigurationError):
    """No project has been selected via ``scaleinn configure``."""


class AuthenticationError(ScaleinnError):
    """Login failed, token missing/expired, or the backend returned HTTP 401."""

    exit_code = EXIT_AUTH


class AuthorizationError(ScaleinnError):
    """The backend returned HTTP 403 (authenticated but not permitted)."""

    exit_code = EXIT_FORBIDDEN


class NetworkError(ScaleinnError):
    """Connection failure, TLS failure or timeout."""

    exit_code = EXIT_NETWORK


class APIError(ScaleinnError):
    """The backend returned an unexpected error status or payload."""

    exit_code = EXIT_API

    def __init__(
        self, message: str, *, status_code: int | None = None, hint: str | None = None
    ) -> None:
        super().__init__(message, hint=hint)
        self.status_code = status_code


class ResponseFormatError(APIError):
    """The backend answered successfully, but the body is not in a recognized shape."""


class ValidationError(ScaleinnError):
    """Invalid user input detected locally."""

    exit_code = EXIT_USAGE
