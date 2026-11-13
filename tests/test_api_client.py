import os

import pytest
import requests

from scaleinn.core import config as cfg
from scaleinn.core import credentials
from scaleinn.core.exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    NetworkError,
    NotConfiguredError,
)
from scaleinn.core.token_manager import make_token_record

from conftest import TEST_REFRESH, TEST_TOKEN


def test_get_sends_bearer_header_params_and_json_headers(http, make_client, logged_in):
    http.add(200, {"ok": True})
    result = make_client().get("/api/v1/x", params={"projectId": "p", "search": ""})
    call = http.calls[0]
    assert result == {"ok": True}
    assert call["method"] == "GET"
    assert call["url"] == "https://app.scaleinn.in:8086/api/v1/x"
    assert call["params"] == {"projectId": "p", "search": ""}
    assert call["headers"]["Authorization"] == f"Bearer {TEST_TOKEN}"
    assert call["headers"]["Accept"] == "application/json"
    assert call["headers"]["Content-Type"] == "application/json"


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete"])
def test_all_http_verbs(http, make_client, logged_in, method):
    http.add(200, {"v": method})
    assert getattr(make_client(), method)("/p") == {"v": method}
    assert http.calls[0]["method"] == method.upper()


def test_post_sends_json_body(http, make_client, logged_in):
    http.add(201, {"id": 1})
    make_client().post("/things", json={"name": "a"})
    assert http.calls[0]["json"] == {"name": "a"}


@pytest.mark.parametrize("url", ["http://192.168.192.234:8080", "https://app.scaleinn.in:8086"])
def test_http_and_https_base_urls_are_used_as_configured(http, make_client, logged_in, url):
    http.add(200, {})
    make_client(api_url=url).get("/ping")
    assert http.calls[0]["url"] == f"{url}/ping"


def test_http_endpoint_prints_security_warning(logged_in, capsys):
    from scaleinn.core.api_client import ApiClient
    from scaleinn.core.token_manager import TokenManager

    config = cfg.update_config(api_url="http://10.0.0.5:8080")
    ApiClient(config, TokenManager(config))
    assert "plain HTTP" in capsys.readouterr().err


def test_ssl_verification_settings(http, make_client, logged_in, tmp_path):
    http.add(200, {})
    make_client().get("/a")
    assert http.calls[0]["verify"] is True

    http.add(200, {})
    make_client(verify_ssl=False).get("/a")
    assert http.calls[1]["verify"] is False

    ca = tmp_path / "ca.pem"
    ca.write_text("pem")
    http.add(200, {})
    make_client(verify_ssl=True, ca_bundle=str(ca)).get("/a")
    assert http.calls[2]["verify"] == str(ca)


def test_missing_ca_bundle_is_a_config_error(make_client):
    with pytest.raises(ConfigurationError):
        make_client(ca_bundle="/nonexistent/ca.pem")


def test_missing_credentials_means_not_logged_in(http, make_client):
    with pytest.raises(NotConfiguredError):
        make_client().get("/x")
    assert http.calls == []  # never reached the network


# ------------------------------------------------------------ HTTP errors
def test_401_without_refresh_asks_to_reauthenticate(http, make_client, logged_in):
    http.add(401, {"message": "bad token"})
    with pytest.raises(AuthenticationError) as info:
        make_client().get("/x")
    assert "scaleinn configure" in info.value.hint
    assert len(http.calls) == 1


def test_401_with_refresh_endpoint_refreshes_and_retries_once(http, make_client, logged_in):
    client = make_client(endpoints={"refresh": "/auth/refresh"})
    http.add(401).add(200, {"access_token": "fresh-token"}).add(200, {"data": 1})
    assert client.get("/x") == {"data": 1}
    assert [c["url"].rsplit("/", 1)[-1] for c in http.calls] == ["x", "refresh", "x"]
    assert http.calls[2]["headers"]["Authorization"] == "Bearer fresh-token"


def test_401_after_refresh_does_not_loop(http, make_client, logged_in):
    client = make_client(endpoints={"refresh": "/auth/refresh"})
    http.add(401).add(200, {"access_token": "t2"}).add(401)
    with pytest.raises(AuthenticationError):
        client.get("/x")
    assert len(http.calls) == 3


def test_failed_refresh_falls_back_to_reauthentication(http, make_client, logged_in):
    client = make_client(endpoints={"refresh": "/auth/refresh"})
    http.add(401).add(401)  # request rejected, refresh rejected
    with pytest.raises(AuthenticationError):
        client.get("/x")


def test_expired_token_is_refreshed_before_the_request(http, make_client):
    credentials.save_credentials(
        make_token_record(TEST_TOKEN, TEST_REFRESH, expires_at="2000-01-01T00:00:00Z")
    )
    client = make_client(endpoints={"refresh": "/auth/refresh"})
    http.add(200, {"access_token": "renewed"}).add(200, {"ok": 1})
    assert client.get("/x") == {"ok": 1}
    assert http.calls[1]["headers"]["Authorization"] == "Bearer renewed"


def test_expired_token_without_refresh_prompts_login(http, make_client):
    credentials.save_credentials(make_token_record(TEST_TOKEN, expires_at="2000-01-01T00:00:00Z"))
    with pytest.raises(AuthenticationError) as info:
        make_client().get("/x")
    assert "expired" in info.value.message
    assert http.calls == []


def test_403_is_an_authorization_error(http, make_client, logged_in):
    http.add(403, {"message": "no access to project"})
    with pytest.raises(AuthorizationError) as info:
        make_client().get("/x")
    assert "no access to project" in info.value.message


def test_server_error_is_reported_and_not_retried(http, make_client, logged_in):
    http.add(500, text="boom")
    with pytest.raises(APIError) as info:
        make_client().post("/create", json={"a": 1})
    assert info.value.status_code == 500
    assert len(http.calls) == 1  # no blind retry of a possibly-creating call


@pytest.mark.parametrize(
    "exc",
    [
        requests.exceptions.ConnectTimeout("t"),
        requests.exceptions.ReadTimeout("t"),
        requests.exceptions.ConnectionError("c"),
        requests.exceptions.SSLError("s"),
        requests.exceptions.RequestException("r"),
    ],
)
def test_network_failures_become_network_errors_without_retry(http, make_client, logged_in, exc):
    http.add(exc=exc)
    with pytest.raises(NetworkError):
        make_client().post("/create", json={})
    assert len(http.calls) == 1


def test_ssl_error_hint_mentions_ca_bundle(http, make_client, logged_in):
    http.add(exc=requests.exceptions.SSLError("bad cert"))
    with pytest.raises(NetworkError) as info:
        make_client().get("/x")
    assert "--ca-bundle" in info.value.hint


def test_empty_and_non_json_bodies(http, make_client, logged_in):
    http.add(204)
    assert make_client().get("/x") is None
    http.add(200, text="<html>not json</html>")
    with pytest.raises(APIError):
        make_client().get("/x")


def test_login_style_401_is_reported_as_rejected_credentials(http, make_client):
    http.add(401)
    with pytest.raises(AuthenticationError) as info:
        make_client().post("/login", json={"u": "x"}, auth=False)
    assert "rejected" in info.value.message
    assert "Authorization" not in http.calls[0]["headers"]


def test_log_file_never_contains_tokens(http, make_client, logged_in):
    from scaleinn.core.logger import setup_logging

    setup_logging(debug=True)
    http.add(200, {"access_token": "leaky-body-token"})
    make_client().get("/x", params={"search": "q"})
    http.add(401)
    with pytest.raises(AuthenticationError):
        make_client().get("/y")
    text = cfg.log_path().read_text()
    assert "GET /x" in text and "HTTP 200" in text
    for secret in (TEST_TOKEN, TEST_REFRESH, "leaky-body-token"):
        assert secret not in text
    assert oct(os.stat(cfg.log_path()).st_mode & 0o777) == "0o600"
