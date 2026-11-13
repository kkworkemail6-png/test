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
    EndpointNotConfiguredError,
    ValidationError,
)

LOGIN_ENDPOINTS = {"root_login": "/auth/root", "iam_login": "/auth/iam", "projects": "/projects"}
PROJECT_LIST = [
    {"projectId": "exch4bt42y", "projectName": "Production", "status": "Active"},
    {"projectId": "dev00000aa", "projectName": "Development", "status": "Active"},
]


# ------------------------------------------------------- login dispatcher
def test_root_login_sends_username_password_without_auth_header(http, make_client):
    client = make_client(endpoints=LOGIN_ENDPOINTS)
    http.add(200, {"access_token": "T", "refresh_token": "R", "expires_in": 3600})
    record = login(client, cfg.load_config(), "root", "root", "pw-123")
    call = http.calls[0]
    assert call["url"].endswith("/auth/root")
    assert call["json"] == {"username": "root", "password": "pw-123"}
    assert "Authorization" not in call["headers"]
    assert record["access_token"] == "T" and record["refresh_token"] == "R"
    assert record["expires_at"]


def test_iam_login_uses_login_id_and_its_own_endpoint(http, make_client):
    client = make_client(endpoints=LOGIN_ENDPOINTS)
    http.add(200, {"accessToken": "T2"})
    record = login(client, cfg.load_config(), "iam", "user@example.com", "pw")
    assert http.calls[0]["url"].endswith("/auth/iam")
    assert http.calls[0]["json"]["loginId"] == "user@example.com"
    assert record["access_token"] == "T2"


@pytest.mark.parametrize("auth_type", ["root", "iam"])
def test_login_without_configured_endpoint_does_not_invent_one(http, make_client, auth_type):
    with pytest.raises(EndpointNotConfiguredError):
        login(make_client(), cfg.load_config(), auth_type, "u", "p")
    assert http.calls == []


def test_unknown_auth_type(make_client):
    with pytest.raises(ValidationError):
        login(make_client(), cfg.load_config(), "admin", "u", "p")


def test_rejected_credentials(http, make_client):
    client = make_client(endpoints=LOGIN_ENDPOINTS)
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
    cfg.update_config(endpoints=LOGIN_ENDPOINTS)
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
    # second request (projects) used the new bearer token
    assert http.calls[1]["headers"]["Authorization"] == "Bearer TOKEN-R"


def test_configure_iam_user_selects_second_project(http):
    cfg.update_config(endpoints=LOGIN_ENDPOINTS)
    http.add(200, {"access_token": "TOKEN-I"}).add(200, PROJECT_LIST)

    result = run_configure([], "2\nme@example.com\npw-iam\n2\n")

    assert result.exit_code == 0, result.output
    assert http.calls[0]["json"] == {"loginId": "me@example.com", "password": "pw-iam"}
    config = json.loads(cfg.config_path().read_text())
    assert (config["auth_type"], config["project_id"]) == ("iam", "dev00000aa")


def test_configure_with_login_endpoint_missing_explains_how_to_proceed(http):
    result = run_configure([], "1\nroot\npw\n")
    assert result.exit_code == 6
    assert "endpoints.root_login" in result.output and "--with-token" in result.output
    assert not cfg.credentials_path().exists()


def test_configure_with_token_and_manual_project_when_projects_api_unknown(http):
    result = run_configure(["--with-token"], "1\nBEARER-TOK-123\nmyproj01\nMy Project\n")
    assert result.exit_code == 0, result.output
    assert json.loads(cfg.credentials_path().read_text())["access_token"] == "BEARER-TOK-123"
    config = json.loads(cfg.config_path().read_text())
    assert (config["project_id"], config["project_name"]) == ("myproj01", "My Project")
    assert "BEARER-TOK-123" not in result.output
    assert http.calls == []


def test_configure_project_only_keeps_login_and_changes_project(http, logged_in):
    cfg.update_config(endpoints={"projects": "/projects"})
    http.add(200, PROJECT_LIST)
    result = run_configure(["--project-only"], "2\n")
    assert result.exit_code == 0, result.output
    assert json.loads(cfg.config_path().read_text())["project_id"] == "dev00000aa"
    assert json.loads(cfg.config_path().read_text())["auth_type"] == "root"  # unchanged
    assert len(http.calls) == 1  # no login call


def test_configure_project_only_requires_login():
    result = run_configure(["--project-only"], "")
    assert result.exit_code == 3


def test_configure_saves_connection_options_without_touching_project(http, logged_in):
    cfg.update_config(endpoints={"projects": "/projects"})
    http.add(200, PROJECT_LIST)
    result = run_configure(["--project-only", "--api-url", "http://10.1.1.1:8080"], "1\n")
    assert result.exit_code == 0
    assert result.output.count("plain HTTP") == 1  # security warning shown once, not repeated
    config = json.loads(cfg.config_path().read_text())
    assert config["api_url"] == "http://10.1.1.1:8080" and config["protocol"] == "http"


def test_configure_no_projects_available(http):
    cfg.update_config(endpoints=LOGIN_ENDPOINTS)
    http.add(200, {"access_token": "T"}).add(200, [])
    assert run_configure([], "1\nroot\npw\n").exit_code == 2


def test_credentials_are_reused_without_reauthenticating(http, logged_in):
    http.add(200, [])
    result = CliRunner().invoke(cli, ["object-storage", "list-buckets", "-o", "json"])
    assert result.exit_code == 0, result.output
    assert len(http.calls) == 1  # no login round-trip
