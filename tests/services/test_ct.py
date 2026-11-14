import json

import pytest
from click.testing import CliRunner

from scaleinn.cli import cli
from scaleinn.core import credentials
from scaleinn.core import config as cfg
from scaleinn.core.exceptions import ValidationError
from scaleinn.services.ct import models

from conftest import TEST_PROJECT, TEST_TOKEN, split_runner

runner = CliRunner()
split = split_runner()
URL = "https://app.scaleinn.in:8443/api/v1/orca/compute/lxc/get-list-by-projectid"


def test_ct_group_and_list_command_are_registered():
    assert cli.commands["ct"].commands["list"] is not None
    result = runner.invoke(cli, ["ct", "--help"])
    assert result.exit_code == 0 and "list" in result.output


def test_ct_list_help_shows_options():
    result = runner.invoke(cli, ["ct", "list", "--help"])
    for option in ("--search", "--page", "--size", "--sort-by", "--sort-direction", "--output"):
        assert option in result.output


def test_ct_list_calls_documented_endpoint_with_default_parameters(http, logged_in):
    http.add(200, [{"name": "ct-1"}])
    result = runner.invoke(cli, ["ct", "list"])
    assert result.exit_code == 0, result.output
    call = http.calls[0]
    assert call["method"] == "GET" and call["url"] == URL
    assert call["params"] == {
        "projectId": TEST_PROJECT,
        "sortBy": "createdDate",
        "sortDirection": "DESC",
        "page": 0,
        "size": 100,
        "search": "",
    }
    assert call["headers"]["Authorization"] == f"Bearer {TEST_TOKEN}"


def test_ct_list_project_id_comes_from_config(http, logged_in):
    credentials.update_context(project=credentials.selection("another-project"))
    http.add(200, [])
    runner.invoke(cli, ["ct", "list"])
    assert http.calls[0]["params"]["projectId"] == "another-project"


def test_ct_list_custom_paging_sorting_and_search(http, logged_in):
    http.add(200, [])
    result = runner.invoke(
        cli,
        ["ct", "list", "--search", "web", "--page", "2", "--size", "25",
         "--sort-by", "name", "--sort-direction", "asc"],
    )
    assert result.exit_code == 0, result.output
    params = http.calls[0]["params"]
    assert params["search"] == "web" and params["page"] == 2 and params["size"] == 25
    assert params["sortBy"] == "name" and params["sortDirection"] == "ASC"


@pytest.mark.parametrize(
    "args", [["--page", "-1"], ["--size", "0"], ["--sort-direction", "sideways"], ["--page", "x"]]
)
def test_ct_list_rejects_invalid_options_before_any_request(http, logged_in, args):
    result = runner.invoke(cli, ["ct", "list", *args])
    assert result.exit_code == 2
    assert http.calls == []


def test_ct_list_json_output_is_the_backend_response(http, logged_in):
    body = {"status": "success", "data": {"content": [{"name": "ct-1"}], "totalElements": 1}}
    http.add(200, body)
    result = split.invoke(cli, ["ct", "list", "--output", "json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == body


def test_ct_list_table_output_looks_through_a_data_envelope(http, logged_in):
    http.add(200, {"data": {"content": [{"name": "ct-1", "status": "running"}], "page": 0}})
    result = split.invoke(cli, ["ct", "list"])
    assert result.exit_code == 0
    assert "| name" in result.stdout and "ct-1" in result.stdout and "running" in result.stdout


def test_ct_list_requires_a_selected_project(http):
    result = runner.invoke(cli, ["ct", "list"])
    assert result.exit_code == 6 and "No project selected" in result.output
    assert http.calls == []


@pytest.mark.parametrize("status,code", [(401, 3), (403, 4), (500, 7)])
def test_ct_list_http_errors(http, logged_in, status, code):
    http.add(status, {"message": "nope"})
    assert runner.invoke(cli, ["ct", "list"]).exit_code == code


def test_ct_model_validation():
    assert models.normalize_search(None) == "" and models.normalize_search(" a ") == "a"
    assert models.normalize_sort_by("") == "createdDate"
    assert models.normalize_sort_direction("asc") == "ASC"
    with pytest.raises(ValidationError):
        models.normalize_search("a\x00b")
    with pytest.raises(ValidationError):
        models.normalize_search("x" * 300)
    with pytest.raises(ValidationError):
        models.normalize_sort_direction("up")
    with pytest.raises(ValidationError):
        models.validate_paging(-1, 10)
    with pytest.raises(ValidationError):
        models.validate_paging(0, 0)
