"""credentials.json holds the token, the selected organisation and project, and the policies."""

import json
import os
import stat

import pytest

from scaleinn.core import config as cfg
from scaleinn.core import credentials
from scaleinn.core.exceptions import NotConfiguredError
from scaleinn.core.session import Session
from scaleinn.core.token_manager import make_token_record

POLICIES = {"data": [{"policyName": "ProjectAdmin"}]}


def read_file():
    return json.loads(cfg.credentials_path().read_text())


def test_context_is_stored_in_the_same_file_as_the_token(logged_in):
    credentials.update_context(policies=POLICIES)
    stored = read_file()
    assert stored["access_token"] and stored["refresh_token"]
    assert stored["organisation"] == {"id": "org-1", "name": "Acme"}
    assert stored["project"] == {"id": "proj1234ab", "name": "Production"}
    assert stored["policies"] == POLICIES


def test_file_permissions_stay_600_after_context_updates(logged_in):
    credentials.update_context(policies=POLICIES)
    assert stat.S_IMODE(os.stat(cfg.credentials_path()).st_mode) == 0o600
    assert [p.name for p in cfg.config_dir().iterdir() if p.name.endswith(".tmp")] == []


def test_update_context_changes_only_the_given_keys(logged_in):
    credentials.update_context(project=credentials.selection("p2", "Two"))
    stored = read_file()
    assert stored["project"] == {"id": "p2", "name": "Two"}
    assert stored["organisation"]["id"] == "org-1"  # untouched
    assert stored["access_token"]


def test_update_context_none_removes_a_key(logged_in):
    credentials.update_context(organisation=None)
    assert "organisation" not in read_file()
    assert credentials.get_organisation() is None
    assert credentials.get_project()["id"] == "proj1234ab"


def test_update_context_rejects_unknown_keys_so_nothing_else_can_be_stored(logged_in):
    with pytest.raises(ValueError):
        credentials.update_context(password="hunter2")
    assert "hunter2" not in cfg.credentials_path().read_text()


def test_update_context_requires_a_login():
    with pytest.raises(NotConfiguredError):
        credentials.update_context(project=credentials.selection("p"))
    assert not cfg.credentials_path().exists()


def test_new_login_clears_the_previous_identity(logged_in):
    credentials.update_context(policies=POLICIES)
    credentials.save_credentials(make_token_record("another-user-token"))
    stored = read_file()
    assert stored["access_token"] == "another-user-token"
    assert not {"organisation", "project", "policies"} & set(stored)


def test_keep_context_preserves_the_selection_and_policies(logged_in):
    credentials.update_context(policies=POLICIES)
    credentials.save_credentials(make_token_record("refreshed"), keep_context=True)
    stored = read_file()
    assert stored["access_token"] == "refreshed"
    assert stored["project"]["id"] == "proj1234ab" and stored["policies"] == POLICIES


def test_save_credentials_ignores_non_whitelisted_keys():
    record = make_token_record("t")
    record["password"] = "hunter2"
    credentials.save_credentials(record)
    assert "hunter2" not in cfg.credentials_path().read_text()


def test_getters_return_nothing_when_logged_out():
    assert credentials.load_credentials() is None
    assert credentials.get_organisation() is None
    assert credentials.get_project() is None
    assert credentials.get_policies() is None
    assert credentials.load_context() == {}


def test_clear_credentials_removes_everything(logged_in):
    credentials.clear_credentials()
    assert not cfg.credentials_path().exists()
    credentials.clear_credentials()  # idempotent


def test_selection_defaults_the_name_to_the_id():
    assert credentials.selection("abc") == {"id": "abc", "name": "abc"}
    assert credentials.selection(7, "Seven") == {"id": "7", "name": "Seven"}


def test_session_exposes_the_stored_context(logged_in):
    credentials.update_context(policies=POLICIES)
    session = Session()
    assert session.project_id == "proj1234ab"
    assert session.organisation == {"id": "org-1", "name": "Acme"}
    assert session.policies == POLICIES


def test_config_json_never_receives_the_selection(logged_in):
    credentials.update_context(project=credentials.selection("p9", "Nine"))
    text = cfg.config_path().read_text() if cfg.config_path().exists() else ""
    assert "p9" not in text and "Acme" not in text
