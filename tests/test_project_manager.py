import json

import pytest
from click.testing import CliRunner

from scaleinn.core import config as cfg
from scaleinn.core import project_manager as pm
from scaleinn.core.exceptions import (
    APIError,
    NotConfiguredError,
    ResponseFormatError,
    ProjectNotSelectedError,
)

PROJECTS = [
    pm.Project("exch4bt42y", "Production", "Active"),
    pm.Project("dev00000aa", "Development", "Active"),
    pm.Project("tst11111bb", "Testing", None),
]


def test_parse_projects_from_list_and_wrapped_dict():
    raw = [{"projectId": "p1", "projectName": "One", "status": "Active"}, {"id": 2, "name": "Two"}]
    assert pm.parse_projects(raw) == [pm.Project("p1", "One", "Active"), pm.Project("2", "Two", None)]
    assert len(pm.parse_projects({"data": raw})) == 2


def test_parse_projects_skips_unusable_items_and_rejects_bad_shape():
    assert pm.parse_projects([{"nothing": 1}, "x"]) == []
    with pytest.raises(APIError):
        pm.parse_projects({"unexpected": "shape"})


def test_render_projects_table_lists_all_projects():
    table = pm.render_projects(PROJECTS)
    for project in PROJECTS:
        assert project.name in table and project.id in table
    assert "| 1 " in table and "| 3 " in table


def test_choose_project_selects_by_number(monkeypatch):
    monkeypatch.setattr("click.prompt", lambda *a, **k: 2)
    assert pm.choose_project(PROJECTS).id == "dev00000aa"


def test_choose_project_rejects_out_of_range():
    # real prompt through CliRunner: 9 is invalid, then 1 is accepted
    import click

    @click.command()
    def cmd():
        click.echo(pm.choose_project(PROJECTS).name)

    result = CliRunner().invoke(cmd, input="9\n1\n")
    assert "Production" in result.output
    assert "not in the range" in result.output


def test_save_selected_project_is_stored_in_credentials_not_config(logged_in):
    cfg.update_config(auth_type="iam", default_output="json")
    pm.save_selected_project(PROJECTS[1])
    stored = json.loads(cfg.credentials_path().read_text())
    assert stored["project"] == {"id": "dev00000aa", "name": "Development"}
    assert stored["access_token"]  # the token is untouched
    config = json.loads(cfg.config_path().read_text())
    assert "project_id" not in config and "project_name" not in config
    assert config["auth_type"] == "iam" and config["default_output"] == "json"


def test_save_selected_project_requires_login():
    with pytest.raises(NotConfiguredError):
        pm.save_selected_project(PROJECTS[0])


def test_selecting_a_project_removes_legacy_config_keys(logged_in):
    cfg.update_config(project_id="legacy", project_name="Legacy")
    pm.save_selected_project(PROJECTS[0])
    config = json.loads(cfg.config_path().read_text())
    assert "project_id" not in config and "project_name" not in config


def test_get_selected_project_id(logged_in):
    assert pm.get_selected_project_id(cfg.load_config()) == "proj1234ab"
    pm.save_selected_project(PROJECTS[2])
    assert pm.get_selected_project_id(cfg.load_config()) == "tst11111bb"


def test_get_selected_project_id_without_selection_raises():
    with pytest.raises(ProjectNotSelectedError):
        pm.get_selected_project_id(cfg.load_config())


def test_legacy_config_project_is_still_read_as_a_fallback():
    cfg.update_config(project_id="abc")
    assert pm.get_selected_project_id(cfg.load_config()) == "abc"


def test_fetch_projects_calls_documented_endpoint_with_bearer_token(http, make_client, logged_in):
    http.add(200, [{"projectId": "p9", "projectName": "Nine"}])
    projects = pm.fetch_projects(make_client())
    assert projects == [pm.Project("p9", "Nine", None)]
    call = http.calls[0]
    assert call["method"] == "GET"
    assert call["url"] == "https://app.scaleinn.in:8443/api/v1/orca/projects/list"
    assert call["params"] == {"search": "", "size": 100, "sortDir": "DESC"}
    assert call["headers"]["Authorization"].startswith("Bearer ")


def test_fetch_projects_unrecognized_shape_is_a_response_format_error(http, make_client, logged_in):
    http.add(200, {"message": "something else"})
    with pytest.raises(ResponseFormatError):
        pm.fetch_projects(make_client())


def test_parse_projects_looks_through_envelopes():
    body = {"data": {"content": [{"id": 7, "name": "Seven"}], "total": 1}}
    assert pm.parse_projects(body) == [pm.Project("7", "Seven", None)]
