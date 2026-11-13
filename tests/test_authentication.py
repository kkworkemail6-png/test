"""Root/IAM authentication and the ``scaleinn configure`` workflow."""

import json

import pytest
from click.testing import CliRunner

from scaleinn.auth.login import login, parse_token_response
from scaleinn.cli import cli
from scaleinn.core import config as cfg
from scaleinn.core import credentials
from scaleinn.core.exceptions import (
    APIError,
    AuthenticationError,
    ValidationError,
)

LOGIN_PATH = "/api/v1/orca/user/login"
PROJECTS_PATH = "/api/v1/orca/projects/list"
PROJECT_LIST = [
    {"projectId": "exch4bt42y", "projectName": "Production", "status": "Active"},
    {"projectId": "dev00000aa", "projectName": "Development", "status": "Active"},
]


# ------------------------------------------------------- login dispatcher
def test_root_login_uses_documented_endpoint_and_payload_without_auth_header(http, make_client):
    client = make_client()
    http.add(200, {"access_token": "T", "refresh_token": "R", "expires_in": 3600})
    record = login(client, cfg.load_config(), "root", "root-test-user", "pw-123")
    call = http.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://app.scaleinn.in:8443" + LOGIN_PATH
    assert call["json"] == {"usernameOrEmail": "root-test-user", "password": "pw-123"}
    assert "Authorization" not in call["headers"]
    assert record["access_token"] == "T" and record["refresh_token"] == "R"
    assert record["expires_at"]


def test_iam_login_sends_the_email_as_usernameOrEmail(http, make_client):
    client = make_client()
    http.add(200, {"accessToken": "T2"})
    record = login(client, cfg.load_config(), "iam", "user@example.com", "pw")
    assert http.calls[0]["url"].endswith(LOGIN_PATH)
    assert http.calls[0]["json"] == {"usernameOrEmail": "user@example.com", "password": "pw"}
    assert record["access_token"] == "T2"


@pytest.mark.parametrize("auth_type,key", [("root", "root_login"), ("iam", "iam_login")])
def test_login_endpoint_can_be_overridden_in_config(http, make_client, auth_type, key):
    client = make_client(endpoints={key: "/custom/login"})
    http.add(200, {"access_token": "T"})
    login(client, cfg.load_config(), auth_type, "u", "p")
    assert http.calls[0]["url"].endswith("/custom/login")


@pytest.mark.parametrize("auth_type", ["root", "iam"])
def test_login_does_not_log_the_password(http, make_client, auth_type):
    from scaleinn.core.logger import register_secret, setup_logging

    setup_logging()
    register_secret("pw-secret-value")
    http.add(200, {"access_token": "T"})
    login(make_client(), cfg.load_config(), auth_type, "u", "pw-secret-value")
    assert "pw-secret-value" not in cfg.log_path().read_text()


def test_unknown_auth_type(make_client):
    with pytest.raises(ValidationError):
        login(make_client(), cfg.load_config(), "admin", "u", "p")


def test_rejected_credentials(http, make_client):
    client = make_client()
    http.add(401, {"message": "invalid"})
    with pytest.raises(AuthenticationError):
        login(client, cfg.load_config(), "root", "root", "wrong")


@pytest.mark.parametrize(
    "body",
    [{"access_token": "a"}, {"accessToken": "a"}, {"token": "a"}, {"data": {"access_token": "a"}}],
)
def test_token_response_variants(body):
    assert parse_token_response(body)["access_token"] == "a"


@pytest.mark.parametrize("body", [{}, {"foo": "bar"}, [], None, "text"])
def test_token_response_without_token_is_an_error(body):
    with pytest.raises(APIError):
        parse_token_response(body)


# --------------------------------------------------- configure workflow
def run_configure(args, user_input):
    return CliRunner().invoke(cli, ["configure", *args], input=user_input)


def test_configure_root_user_end_to_end(http):
    http.add(200, {"access_token": "TOKEN-R", "refresh_token": "REF-R", "expires_in": 3600})
    http.add(200, PROJECT_LIST)

    result = run_configure([], "1\nroot\ns3cret-pass\n1\n")

    assert result.exit_code == 0, result.output
    for text in ("Welcome to Scaleinn CLI", "Authentication successful!", "Production",
                 "Project selected successfully!", "Project ID: exch4bt42y",
                 "Scaleinn CLI configuration completed."):
        assert text in result.output
    assert "s3cret-pass" not in result.output  # password never echoed

    config = json.loads(cfg.config_path().read_text())
    assert (config["auth_type"], config["project_id"], config["project_name"]) == (
        "root", "exch4bt42y", "Production")
    stored = json.loads(cfg.credentials_path().read_text())
    assert stored["access_token"] == "TOKEN-R" and stored["refresh_token"] == "REF-R"
    # the password is not stored anywhere on disk or in the log
    for path in (cfg.config_path(), cfg.credentials_path(), cfg.log_path()):
        assert "s3cret-pass" not in path.read_text()
    assert "TOKEN-R" not in cfg.log_path().read_text()
    # second request is the accessible-projects API, sent with the new bearer token
    assert http.calls[1]["url"] == "https://app.scaleinn.in:8443" + PROJECTS_PATH
    assert http.calls[1]["params"] == {"search": "", "size": 100, "sortDir": "DESC"}
    assert http.calls[1]["headers"]["Authorization"] == "Bearer TOKEN-R"


def test_configure_iam_user_selects_second_project(http):
    http.add(200, {"access_token": "TOKEN-I"}).add(200, PROJECT_LIST)

    result = run_configure([], "2\nme@example.com\npw-iam\n2\n")

    assert result.exit_code == 0, result.output
    assert http.calls[0]["json"] == {"usernameOrEmail": "me@example.com", "password": "pw-iam"}
    config = json.loads(cfg.config_path().read_text())
    assert (config["auth_type"], config["project_id"]) == ("iam", "dev00000aa")


def test_configure_falls_back_to_manual_project_when_projects_response_is_not_understood(http):
    """The projects response schema is unconfirmed: an unrecognized body means manual entry."""
    http.add(200, {"accessToken": "TOK-1", "refreshToken": "REF-1"})
    http.add(200, {"unexpected": "shape"})
    result = run_configure([], "1\nroot-test-user\npw-xyz\nexch4bt42y\nProduction\n")
    assert result.exit_code == 0, result.output
    assert len(http.calls) == 2 and http.calls[0]["url"].endswith(LOGIN_PATH)
    assert http.calls[1]["url"].endswith(PROJECTS_PATH)
    assert "Authentication successful!" in result.output
    assert "Enter the project details manually" in result.output
    assert json.loads(cfg.credentials_path().read_text())["access_token"] == "TOK-1"
    config = json.loads(cfg.config_path().read_text())
    assert (config["auth_type"], config["project_id"]) == ("root", "exch4bt42y")
    assert "pw-xyz" not in result.output + cfg.config_path().read_text() + cfg.log_path().read_text()


def test_configure_wrong_password_stores_nothing(http):
    http.add(401, {"message": "bad credentials"})
    result = run_configure([], "1\nroot-test-user\nwrong\n")
    assert result.exit_code == 3
    assert "rejected" in result.output
    assert not cfg.credentials_path().exists()
    assert not cfg.config_path().exists() or json.loads(cfg.config_path().read_text())["project_id"] is None


def test_configure_projects_api_http_errors_are_not_swallowed(http):
    http.add(200, {"access_token": "T"}).add(403, {"message": "no access"})
    result = run_configure([], "1\nroot-test-user\npw\n")
    assert result.exit_code == 4  # shown as an error, not turned into manual entry
    assert "Enter the project details manually" not in result.output


def test_configure_login_response_without_token_is_an_error(http):
    http.add(200, {"message": "ok but no token"})
    result = run_configure([], "1\nroot-test-user\npw\n")
    assert result.exit_code == 7
    assert not cfg.credentials_path().exists()


def test_configure_with_token_skips_login_and_lists_projects(http):
    http.add(200, {"data": {"content": PROJECT_LIST}})  # projects inside a data envelope
    result = run_configure(["--with-token"], "1\nBEARER-TOK-123\n2\n")
    assert result.exit_code == 0, result.output
    assert json.loads(cfg.credentials_path().read_text())["access_token"] == "BEARER-TOK-123"
    config = json.loads(cfg.config_path().read_text())
    assert (config["project_id"], config["project_name"]) == ("dev00000aa", "Development")
    assert "BEARER-TOK-123" not in result.output
    assert len(http.calls) == 1 and http.calls[0]["url"].endswith(PROJECTS_PATH)
    assert http.calls[0]["headers"]["Authorization"] == "Bearer BEARER-TOK-123"


def test_configure_project_only_keeps_login_and_changes_project(http, logged_in):
    http.add(200, PROJECT_LIST)
    result = run_configure(["--project-only"], "2\n")
    assert result.exit_code == 0, result.output
    assert json.loads(cfg.config_path().read_text())["project_id"] == "dev00000aa"
    assert json.loads(cfg.config_path().read_text())["auth_type"] == "root"  # unchanged
    assert len(http.calls) == 1  # no login call


def test_configure_project_only_requires_login():
    result = run_configure(["--project-only"], "")
    assert result.exit_code == 3


def test_configure_saves_url_overrides_without_touching_project(http, logged_in):
    http.add(200, PROJECT_LIST)
    result = run_configure(
        ["--project-only", "--api-url", "http://10.1.1.1:8080/", "--object-storage-url", "http://10.1.1.1:9000"],
        "1\n",
    )
    assert result.exit_code == 0
    assert result.output.count("plain HTTP") == 1  # security warning shown once, not repeated
    config = json.loads(cfg.config_path().read_text())
    assert config["api_url"] == "http://10.1.1.1:8080"  # trailing slash removed
    assert config["object_storage_url"] == "http://10.1.1.1:9000"
    assert http.calls[0]["url"].startswith("http://10.1.1.1:8080/")


def test_configure_protocol_switches_environment_and_resets_overrides(http, logged_in):
    cfg.update_config(api_url="https://pinned.example:1111", object_storage_url="https://pinned.example:2222")
    http.add(200, PROJECT_LIST)
    result = run_configure(["--project-only", "--protocol", "http"], "1\n")
    assert result.exit_code == 0, result.output
    config = json.loads(cfg.config_path().read_text())
    assert config["protocol"] == "http"
    assert config["api_url"] is None and config["object_storage_url"] is None  # back to env defaults
    assert http.calls[0]["url"].startswith("http://")
    assert "pinned.example" not in http.calls[0]["url"]


def test_configure_rejects_invalid_url_option():
    assert run_configure(["--project-only", "--api-url", "not-a-url"], "").exit_code == 6


def test_configure_no_projects_available(http):
    http.add(200, {"access_token": "T"}).add(200, [])
    assert run_configure([], "1\nroot\npw\n").exit_code == 2


def test_credentials_are_reused_without_reauthenticating(http, logged_in):
    http.add(200, [])
    result = CliRunner().invoke(cli, ["object-storage", "list-buckets", "-o", "json"])
    assert result.exit_code == 0, result.output
    assert len(http.calls) == 1  # no login round-trip
