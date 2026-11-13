"""The one and only HTTP client used to talk to the Scaleinn backend.

Resource modules (object storage, CT, ...) must never use ``requests`` directly;
they call ``client.get/post/put/patch/delete`` so that authentication, TLS
settings, timeouts, error mapping and sanitized logging live in one place.

Retry policy: requests are **not** retried automatically, with a single
exception. If the backend answers HTTP 401 and a refresh token is available, the
token is refreshed and the request is replayed once; a 401 means the backend did
not process the request, so this cannot create duplicate resources. Timeouts,
connection errors and 5xx responses are never retried because the operation may
already have taken effect.
"""

from __future__ import annotations

from typing import Any

import requests
import urllib3

from scaleinn.core.config import connection_warnings
from scaleinn.core.exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    NetworkError,
    ScaleinnError,
)
from scaleinn.core.logger import get_logger
from scaleinn.core.token_manager import TokenManager
from scaleinn.utils import terminal

log = get_logger("api")

CONNECT_TIMEOUT = 10
DEFAULT_READ_TIMEOUT = 30


class ApiClient:
    def __init__(
        self,
        config: dict[str, Any],
        token_manager: TokenManager,
        http: requests.Session | None = None,
        warn: bool = True,
    ) -> None:
        self._config = config
        self._tokens = token_manager
        self._http = http or requests.Session()
        self.base_url: str = config["api_url"]
        self._verify = self._resolve_verify(config)
        self._timeout = (CONNECT_TIMEOUT, config.get("timeout") or DEFAULT_READ_TIMEOUT)

        for message in connection_warnings(config):
            if warn:
                terminal.warn_once(message)
            log.warning(message)
        if config["protocol"] == "https" and not config["verify_ssl"]:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # ----------------------------------------------------------- helpers
    @staticmethod
    def _resolve_verify(config: dict[str, Any]) -> bool | str:
        ca_bundle = config.get("ca_bundle")
        if ca_bundle:
            from pathlib import Path

            if not Path(ca_bundle).expanduser().is_file():
                raise ConfigurationError(
                    f"CA bundle not found: {ca_bundle}",
                    hint="Fix 'ca_bundle' in ~/.scaleinn/config.json or run 'scaleinn configure --ca-bundle PATH'.",
                )
            return str(Path(ca_bundle).expanduser())
        return bool(config["verify_ssl"])

    def _url(self, path: str) -> str:
        return self.base_url + (path if path.startswith("/") else "/" + path)

    @staticmethod
    def _error_message(response: requests.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            for key in ("message", "error", "detail", "msg"):
                value = body.get(key)
                if isinstance(value, str) and value:
                    return value
        text = (response.text or "").strip()
        return text[:200] if text else (response.reason or "no details provided")

    def _ensure_fresh_token(self) -> None:
        """Refresh proactively when the stored expiry has passed."""
        if not self._tokens.is_expired():
            return
        log.info("Access token expired")
        try:
            self._tokens.refresh(self)
        except ScaleinnError as exc:
            raise AuthenticationError(
                "Your session has expired.", hint="Run 'scaleinn configure' to sign in again."
            ) from exc

    def _try_refresh(self) -> bool:
        if not self._tokens.can_refresh():
            return False
        try:
            self._tokens.refresh(self)
            return True
        except ScaleinnError:
            return False

    # ----------------------------------------------------------- request
    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        auth: bool = True,
        _retried: bool = False,
    ) -> Any:
        """Send a request and return the parsed JSON body (``None`` if empty).

        Args:
            auth: Attach the bearer token. Login/refresh calls pass ``False``.

        Request bodies and headers are never logged.
        """
        method = method.upper()
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if auth:
            self._ensure_fresh_token()
            headers["Authorization"] = f"{self._tokens.token_type} {self._tokens.access_token}"

        log.info("%s %s", method, path)
        if params:
            log.debug("Query parameters: %s", params)

        try:
            response = self._http.request(
                method,
                self._url(path),
                params=params,
                json=json,
                headers=headers,
                timeout=self._timeout,
                verify=self._verify,
            )
        except requests.exceptions.SSLError as exc:
            log.error("TLS error: %s", type(exc).__name__)
            raise NetworkError(
                "TLS/SSL verification failed while connecting to the Scaleinn backend.",
                hint="Check the server certificate, set a CA bundle with "
                "'scaleinn configure --ca-bundle PATH', or (development only) "
                "'scaleinn configure --no-verify-ssl'.",
            ) from exc
        except requests.exceptions.Timeout as exc:
            log.error("Request timed out")
            raise NetworkError(
                "The request to the Scaleinn backend timed out.",
                hint="Check your network connection and try again.",
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            log.error("Connection failed: %s", type(exc).__name__)
            raise NetworkError(
                f"Could not connect to the Scaleinn backend at {self.base_url}.",
                hint="Check the API URL ('scaleinn configure --api-url ...') and your network.",
            ) from exc
        except requests.exceptions.RequestException as exc:
            log.error("Request failed: %s", type(exc).__name__)
            raise NetworkError(f"Request failed: {type(exc).__name__}.") from exc

        log.info("Backend response received: HTTP %s", response.status_code)
        return self._handle_response(method, path, response, params, json, auth, _retried)

    def _handle_response(
        self,
        method: str,
        path: str,
        response: requests.Response,
        params: dict[str, Any] | None,
        json: Any,
        auth: bool,
        retried: bool,
    ) -> Any:
        status = response.status_code

        if status == 401:
            if not auth:
                raise AuthenticationError("Authentication failed: the credentials were rejected.")
            if not retried and self._try_refresh():
                log.info("Retrying request once after token refresh")
                return self.request(method, path, params=params, json=json, auth=True, _retried=True)
            raise AuthenticationError(
                "Your session is invalid or has expired (HTTP 401).",
                hint="Run 'scaleinn configure' to sign in again.",
            )
        if status == 403:
            raise AuthorizationError(
                f"Access denied (HTTP 403): {self._error_message(response)}",
                hint="Check that your user has permission for this action in the selected project.",
            )
        if status >= 400:
            raise APIError(
                f"The backend returned HTTP {status}: {self._error_message(response)}",
                status_code=status,
            )

        if status == 204 or not (response.content or b"").strip():
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise APIError(
                f"The backend returned a non-JSON response (HTTP {status}).", status_code=status
            ) from exc

    # ---------------------------------------------------- HTTP verbs
    def get(self, path: str, params: dict[str, Any] | None = None, **kw: Any) -> Any:
        return self.request("GET", path, params=params, **kw)

    def post(self, path: str, json: Any = None, params: dict[str, Any] | None = None, **kw: Any) -> Any:
        return self.request("POST", path, params=params, json=json, **kw)

    def put(self, path: str, json: Any = None, params: dict[str, Any] | None = None, **kw: Any) -> Any:
        return self.request("PUT", path, params=params, json=json, **kw)

    def patch(self, path: str, json: Any = None, params: dict[str, Any] | None = None, **kw: Any) -> Any:
        return self.request("PATCH", path, params=params, json=json, **kw)

    def delete(self, path: str, params: dict[str, Any] | None = None, **kw: Any) -> Any:
        return self.request("DELETE", path, params=params, **kw)
