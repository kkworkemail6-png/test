"""Access/refresh token lifecycle: storage, expiry tracking and refresh."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from scaleinn.core import credentials as store
from scaleinn.core.exceptions import AuthenticationError, NotConfiguredError
from scaleinn.core.logger import get_logger, register_secret

if TYPE_CHECKING:  # pragma: no cover
    from scaleinn.core.api_client import ApiClient

log = get_logger("token")

EXPIRY_SKEW_SECONDS = 30  # treat tokens as expired slightly early


def parse_expiry(value: Any) -> datetime | None:
    """Parse an ISO-8601 string or epoch seconds into an aware UTC datetime."""
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        text = str(value).strip().replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def make_token_record(
    access_token: str,
    refresh_token: str | None = None,
    token_type: str | None = None,
    expires_in: int | float | None = None,
    expires_at: Any = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build the dict stored in ``credentials.json``.

    ``expires_at`` (absolute) wins over ``expires_in`` (seconds from now).
    """
    now = now or datetime.now(timezone.utc)
    expiry = parse_expiry(expires_at)
    if expiry is None and expires_in is not None:
        try:
            expiry = now + timedelta(seconds=float(expires_in))
        except (TypeError, ValueError):
            expiry = None
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": token_type or "Bearer",
        "expires_at": expiry.isoformat() if expiry else None,
    }


class TokenManager:
    """Reads tokens from disk lazily and keeps them in sync after refresh."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._record: dict[str, Any] | None = None
        self._loaded = False

    # ------------------------------------------------------------- state
    def _load(self) -> dict[str, Any] | None:
        if not self._loaded:
            self._record = store.load_credentials()
            self._loaded = True
            if self._record:
                log.info("Authentication loaded")
                register_secret(self._record.get("access_token"))
                register_secret(self._record.get("refresh_token"))
        return self._record

    def reload(self) -> None:
        self._loaded = False
        self._record = None

    @property
    def has_credentials(self) -> bool:
        return self._load() is not None

    @property
    def access_token(self) -> str:
        record = self._load()
        if not record:
            raise NotConfiguredError(
                "You are not logged in.", hint="Run 'scaleinn configure' to sign in."
            )
        return record["access_token"]

    @property
    def token_type(self) -> str:
        record = self._load() or {}
        return record.get("token_type") or "Bearer"

    @property
    def refresh_token(self) -> str | None:
        return (self._load() or {}).get("refresh_token")

    # ------------------------------------------------------------ expiry
    def is_expired(self, skew: int = EXPIRY_SKEW_SECONDS) -> bool:
        """True only if an expiry is known and has passed."""
        expiry = parse_expiry((self._load() or {}).get("expires_at"))
        if expiry is None:
            return False
        return datetime.now(timezone.utc) + timedelta(seconds=skew) >= expiry

    # ----------------------------------------------------------- storage
    def store(self, record: dict[str, Any], keep_context: bool = False) -> None:
        """Persist tokens. A new login (default) clears the stored organisation, project
        and policies; a refresh passes ``keep_context=True`` to keep them."""
        store.save_credentials(record, keep_context=keep_context)
        self.reload()
        self._load()
        log.info("Tokens stored")

    def clear(self) -> None:
        store.clear_credentials()
        self.reload()

    # ----------------------------------------------------------- refresh
    def can_refresh(self) -> bool:
        from scaleinn.auth.refresh import refresh_supported

        return bool(self.refresh_token) and refresh_supported(self._config)

    def refresh(self, client: "ApiClient") -> None:
        """Exchange the refresh token for new tokens and persist them.

        Raises :class:`AuthenticationError` if refresh is impossible or rejected,
        in which case the caller should ask the user to run ``scaleinn configure``.
        """
        from scaleinn.auth.refresh import refresh_tokens

        if not self.can_refresh():
            raise AuthenticationError(
                "Session expired.", hint="Run 'scaleinn configure' to sign in again."
            )
        log.info("Refreshing access token")
        record = refresh_tokens(client, self._config, self.refresh_token)
        if not record.get("refresh_token"):  # keep the old one if backend doesn't rotate it
            record["refresh_token"] = self.refresh_token
        self.store(record, keep_context=True)  # same user: keep organisation, project, policies
