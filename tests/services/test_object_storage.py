import json

import pytest
from click.testing import CliRunner

from scaleinn.cli import cli
from scaleinn.core.exceptions import ValidationError
from scaleinn.services.object_storage.models import normalize_search

from conftest import TEST_PROJECT, TEST_TOKEN, split_runner

runner = CliRunner()
split = split_runner()  # separate stdout/stderr, for tests that parse stdout
URL = "https://app.scaleinn.in:8086/api/v1/object-storage/bucket/get-all-bucket"


def test_list_buckets_calls_documented_endpoint_with_selected_project(http, logged_in):
    http.add(200, [{"name": "my-bucket"}])
    result = runner.invoke(cli, ["object-storage", "list-buckets"])
    assert result.exit_code == 0, result.output
    call = http.calls[0]
    assert call["method"] == "GET" and call["url"] == URL
    assert call["params"] == {"projectId": TEST_PROJECT, "search": ""}
    assert call["headers"]["Authorization"] == f"Bearer {TEST_TOKEN}"


def test_project_id_comes_from_config_not_code(http, logged_in):
    from scaleinn.core import config as cfg

    cfg.update_config(project_id="another-project")
    http.add(200, [])
    runner.invoke(cli, ["object-storage", "list-buckets"])
    assert http.calls[0]["params"]["projectId"] == "another-project"


def test_search_option(http, logged_in):
    http.add(200, [])
    runner.invoke(cli, ["object-storage", "list-buckets", "--search", "my-bucket"])
    assert http.calls[0]["params"]["search"] == "my-bucket"


def test_json_output_shows_backend_response_verbatim(http, logged_in):
    body = {"status": "success", "data": {"buckets": [], "page": 1}}
    http.add(200, body)
    result = split.invoke(cli, ["object-storage", "list-buckets", "--output", "json"])
    assert json.loads(result.stdout) == body


def test_table_output_for_list_of_records(http, logged_in):
    http.add(200, {"data": [{"name": "b1", "size": 3}, {"name": "b2", "size": 5}]})
    result = split.invoke(cli, ["object-storage", "list-buckets", "--output", "table"])
    assert result.exit_code == 0
    assert "| name" in result.stdout and "b1" in result.stdout and "b2" in result.stdout


def test_table_output_falls_back_to_json_for_unknown_shape(http, logged_in):
    http.add(200, {"data": {"buckets": 3}})
    result = split.invoke(cli, ["object-storage", "list-buckets"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"data": {"buckets": 3}}  # stdout stays valid JSON
    assert "not mapped to a table" in result.stderr  # the note goes to stderr


def test_empty_result(http, logged_in):
    http.add(200, [])
    result = runner.invoke(cli, ["object-storage", "list-buckets"])
    assert "No results found." in result.output


def test_invalid_output_choice():
    assert runner.invoke(cli, ["object-storage", "list-buckets", "-o", "xml"]).exit_code == 2


def test_object_storage_help():
    result = runner.invoke(cli, ["object-storage", "--help"])
    assert result.exit_code == 0 and "list-buckets" in result.output


def test_search_validation():
    assert normalize_search(None) == "" and normalize_search("  x ") == "x"
    with pytest.raises(ValidationError):
        normalize_search("a\x00b")
    with pytest.raises(ValidationError):
        normalize_search("x" * 300)
