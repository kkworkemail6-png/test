"""Root/IAM authentication and the ``scaleinn configure`` workflow."""

import json
from urllib.parse import urlsplit

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
ORGS_PATH = "/api/v1/orca/organisation/list"
POLICIES_PATH = "/api/v1/orca/policies/my-policies"
PROJECT_LIST = [
    {"projectId": "exch4bt42y", "projectName": "Production", "status": "Active"},
    {"projectId": "dev00000aa", "projectName": "Development", "status": "Active"},
]
ORG_LIST = [
    {"organisationId": "org-aaa", "organisationName": "Acme"},
    {"organisationId": "org-bbb", "organisationName": "Globex"},
]
POLICIES = {"status": "success", "data": [{"policyName": "ProjectAdmin", "actions": ["ct:list"]}]}


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


def stored_credentials():
    return json.loads(cfg.credentials_path().read_text())


def test_configure_root_user_end_to_end(http):
    http.add(200, {"access_token": "TOKEN-R", "refresh_token": "REF-R", "expires_in": 3600})
    http.add(200, ORG_LIST).add(200, PROJECT_LIST).add(200, POLICIES)

    result = run_configure([], "1\nroot\ns3cret-pass\n2\n1\n")

    assert result.exit_code == 0, result.output
    for text in ("Welcome to Scaleinn CLI", "Authentication successful!", "Globex", "Production",
                 "Project selected successfully!", "Selected organisation: Globex",
                 "Organisation ID: org-bbb", "Project ID: exch4bt42y", "Policies loaded.",
                 "Scaleinn CLI configuration completed."):
        assert text in result.output
    assert "s3cret-pass" not in result.output  # password never echoed

    # everything tied to the login lives in credentials.json, next to the token
    stored = stored_credentials()
    assert stored["access_token"] == "TOKEN-R" and stored["refresh_token"] == "REF-R"
    assert stored["organisation"] == {"id": "org-bbb", "name": "Globex"}
    assert stored["project"] == {"id": "exch4bt42y", "name": "Production"}
    assert stored["policies"] == POLICIES  # the raw my-policies response
    # config.json keeps settings only
    config = json.loads(cfg.config_path().read_text())
    assert config["auth_type"] == "root"
    assert "project_id" not in config and "project_name" not in config
    # the password and the token are not stored in config or logs
    for path in (cfg.config_path(), cfg.credentials_path(), cfg.log_path()):
        assert "s3cret-pass" not in path.read_text()
    assert "TOKEN-R" not in cfg.log_path().read_text()
    # request order: login, organisations, projects, policies, each with the new bearer token
    base = "https://app.scaleinn.in:8443"
    assert [c["url"] for c in http.calls] == [
        base + LOGIN_PATH, base + ORGS_PATH, base + PROJECTS_PATH, base + POLICIES_PATH]
    assert http.calls[1]["params"] == {"size": 100, "search": ""}
    assert http.calls[2]["params"] == {"search": "", "size": 100, "sortDir": "DESC"}
    assert http.calls[3]["params"] == {"projectId": "exch4bt42y"}  # policies for the chosen project
    assert all(c["headers"]["Authorization"] == "Bearer TOKEN-R" for c in http.calls[1:])


def test_configure_iam_user_selects_second_project(http):
    http.add(200, {"access_token": "TOKEN-I"}).add(200, ORG_LIST).add(200, PROJECT_LIST).add(200, POLICIES)

    result = run_configure([], "2\nme@example.com\npw-iam\n1\n2\n")

    assert result.exit_code == 0, result.output
    assert http.calls[0]["json"] == {"usernameOrEmail": "me@example.com", "password": "pw-iam"}
    assert json.loads(cfg.config_path().read_text())["auth_type"] == "iam"
    stored = stored_credentials()
    assert stored["project"] == {"id": "dev00000aa", "name": "Development"}
    assert stored["organisation"]["id"] == "org-aaa"
    assert http.calls[3]["params"] == {"projectId": "dev00000aa"}


def test_configure_falls_back_to_manual_project_when_projects_response_is_not_understood(http):
    """The projects response schema is unconfirmed: an unrecognized body means manual entry."""
    http.add(200, {"accessToken": "TOK-1", "refreshToken": "REF-1"})
    http.add(200, ORG_LIST).add(200, {"unexpected": "shape"}).add(200, POLICIES)
    result = run_configure([], "1\nroot-test-user\npw-xyz\n1\nexch4bt42y\nProduction\n")
    assert result.exit_code == 0, result.output
    assert len(http.calls) == 4 and http.calls[0]["url"].endswith(LOGIN_PATH)
    assert http.calls[2]["url"].endswith(PROJECTS_PATH)
    assert "Enter the project details manually" in result.output
    stored = stored_credentials()
    assert stored["access_token"] == "TOK-1"
    assert stored["project"] == {"id": "exch4bt42y", "name": "Production"}
    assert json.loads(cfg.config_path().read_text())["auth_type"] == "root"
    assert "pw-xyz" not in result.output + cfg.config_path().read_text() + cfg.log_path().read_text()


def test_configure_wrong_password_stores_nothing(http):
    http.add(401, {"message": "bad credentials"})
    result = run_configure([], "1\nroot-test-user\nwrong\n")
    assert result.exit_code == 3
    assert "rejected" in result.output
    assert not cfg.credentials_path().exists()
    assert len(http.calls) == 1  # nothing else is requested after a failed login


def test_configure_organisation_forbidden_is_a_warning_not_a_failure(http):
    http.add(200, {"access_token": "T"}).add(403, {"message": "no access"})
    http.add(200, PROJECT_LIST).add(200, POLICIES)
    result = run_configure([], "1\nroot\npw\n1\n")
    assert result.exit_code == 0, result.output
    assert "Continuing without an organisation" in result.output
    stored = stored_credentials()
    assert "organisation" not in stored and stored["project"]["id"] == "exch4bt42y"
    assert "Selected organisation" not in result.output


def test_configure_no_organisations_returned_continues(http):
    http.add(200, {"access_token": "T"}).add(200, []).add(200, PROJECT_LIST).add(200, POLICIES)
    result = run_configure([], "1\nroot\npw\n1\n")
    assert result.exit_code == 0, result.output
    assert "No organisations were returned" in result.output
    assert "organisation" not in stored_credentials()


def test_configure_unrecognized_organisation_response_can_be_entered_manually_or_skipped(http):
    http.add(200, {"access_token": "T"}).add(200, {"unexpected": "shape"})
    http.add(200, PROJECT_LIST).add(200, POLICIES)
    result = run_configure([], "1\nroot\npw\norg-manual\nManual Org\n1\n")
    assert result.exit_code == 0, result.output
    assert stored_credentials()["organisation"] == {"id": "org-manual", "name": "Manual Org"}


def test_configure_organisation_can_be_skipped_when_response_is_not_understood(http):
    http.add(200, {"access_token": "T"}).add(200, {"unexpected": "shape"})
    http.add(200, PROJECT_LIST).add(200, POLICIES)
    result = run_configure([], "1\nroot\npw\n\n1\n")  # empty organisation id = skip
    assert result.exit_code == 0, result.output
    assert "organisation" not in stored_credentials()


def test_configure_projects_api_http_errors_are_not_swallowed(http):
    http.add(200, {"access_token": "T"}).add(200, ORG_LIST).add(403, {"message": "no access"})
    result = run_configure([], "1\nroot-test-user\npw\n1\n")
    assert result.exit_code == 4  # shown as an error, not turned into manual entry
    assert "Enter the project details manually" not in result.output


def test_configure_policies_failure_does_not_fail_configure_and_stores_no_stale_policies(http):
    http.add(200, {"access_token": "T"}).add(200, ORG_LIST).add(200, PROJECT_LIST)
    http.add(500, {"message": "boom"})
    result = run_configure([], "1\nroot\npw\n1\n1\n")
    assert result.exit_code == 0, result.output
    assert "Could not load your policies" in result.output
    stored = stored_credentials()
    assert "policies" not in stored and stored["project"]["id"] == "exch4bt42y"
    assert "Scaleinn CLI configuration completed." in result.output


def test_configure_login_response_without_token_is_an_error(http):
    http.add(200, {"message": "ok but no token"})
    result = run_configure([], "1\nroot-test-user\npw\n")
    assert result.exit_code == 7
    assert not cfg.credentials_path().exists()


def test_configure_with_token_skips_login_and_lists_organisations_and_projects(http):
    http.add(200, ORG_LIST).add(200, {"data": {"content": PROJECT_LIST}})  # projects in an envelope
    http.add(200, POLICIES)
    result = run_configure(["--with-token"], "1\nBEARER-TOK-123\n1\n2\n")
    assert result.exit_code == 0, result.output
    stored = stored_credentials()
    assert stored["access_token"] == "BEARER-TOK-123"
    assert stored["project"] == {"id": "dev00000aa", "name": "Development"}
    assert stored["organisation"]["id"] == "org-aaa"
    assert "BEARER-TOK-123" not in result.output
    assert [urlsplit(c["url"]).path for c in http.calls] == [
        ORGS_PATH, PROJECTS_PATH, POLICIES_PATH]
    assert http.calls[0]["headers"]["Authorization"] == "Bearer BEARER-TOK-123"


def test_reconfigure_replaces_everything_from_the_previous_login(http, logged_in):
    """A new login is a new identity: old organisation, project and policies must not survive."""
    credentials.update_context(policies={"old": "policies"})
    http.add(200, {"access_token": "NEW-TOKEN"}).add(200, []).add(200, PROJECT_LIST).add(200, POLICIES)
    result = run_configure([], "2\nother@example.com\npw\n2\n")
    assert result.exit_code == 0, result.output
    stored = stored_credentials()
    assert stored["access_token"] == "NEW-TOKEN"
    assert "organisation" not in stored  # Acme belonged to the previous user
    assert stored["project"] == {"id": "dev00000aa", "name": "Development"}
    assert stored["policies"] == POLICIES


def test_configure_project_only_keeps_login_and_organisation_and_reloads_policies(http, logged_in):
    http.add(200, PROJECT_LIST).add(200, POLICIES)
    result = run_configure(["--project-only"], "2\n")
    assert result.exit_code == 0, result.output
    stored = stored_credentials()
    assert stored["project"] == {"id": "dev00000aa", "name": "Development"}
    assert stored["organisation"] == {"id": "org-1", "name": "Acme"}  # kept
    assert stored["policies"] == POLICIES
    assert json.loads(cfg.config_path().read_text())["auth_type"] == "root"  # unchanged
    assert [urlsplit(c["url"]).path for c in http.calls] == [PROJECTS_PATH, POLICIES_PATH]
    assert http.calls[1]["params"] == {"projectId": "dev00000aa"}  # no login, no organisation call


def test_configure_project_only_requires_login():
    result = run_configure(["--project-only"], "")
    assert result.exit_code == 3


def test_configure_saves_url_overrides_without_touching_project(http, logged_in):
    http.add(200, PROJECT_LIST).add(200, POLICIES)
    result = run_configure(
        ["--project-only", "--api-url", "http://10.1.1.1:8080/", "--object-storage-url", "http://10.1.1.1:9000"],
        "1\n",
    )
    assert result.exit_code == 0, result.output
    assert result.output.count("plain HTTP") == 1  # security warning shown once, not repeated
    config = json.loads(cfg.config_path().read_text())
    assert config["api_url"] == "http://10.1.1.1:8080"  # trailing slash removed
    assert config["object_storage_url"] == "http://10.1.1.1:9000"
    assert http.calls[0]["url"].startswith("http://10.1.1.1:8080/")


def test_configure_protocol_switches_environment_and_resets_overrides(http, logged_in):
    cfg.update_config(api_url="https://pinned.example:1111", object_storage_url="https://pinned.example:2222")
    http.add(200, PROJECT_LIST).add(200, POLICIES)
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
    http.add(200, {"access_token": "T"}).add(200, ORG_LIST).add(200, [])
    assert run_configure([], "1\nroot\npw\n1\n").exit_code == 2


def test_credentials_are_reused_without_reauthenticating(http, logged_in):
    http.add(200, [])
    result = CliRunner().invoke(cli, ["object-storage", "list-buckets", "-o", "json"])
    assert result.exit_code == 0, result.output
    assert len(http.calls) == 1  # no login round-trip
