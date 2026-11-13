"""CLI startup, help/version, exit codes, output formatting and log sanitization."""

import json

import pytest
from click.testing import CliRunner

from scaleinn.cli import cli
from scaleinn.core import config as cfg
from scaleinn.core.logger import REDACTED, register_secret, sanitize
from scaleinn.utils.json_formatter import format_json
from scaleinn.utils.table_formatter import extract_rows, format_table
from scaleinn.version import __version__

from conftest import TEST_TOKEN, split_runner

runner = CliRunner()
split = split_runner()


def test_version_flag_and_command():
    for args in (["--version"], ["version"]):
        result = runner.invoke(cli, args)
        assert result.exit_code == 0
        assert f"scaleinn-cli/{__version__}" in result.output


def test_help_lists_all_commands():
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for name in ("configure", "object-storage", "ct", "version", "--debug"):
        assert name in result.output


def test_help_and_version_do_not_touch_disk_or_network(http):
    runner.invoke(cli, ["--help"])
    runner.invoke(cli, ["--version"])
    assert not cfg.config_dir().exists()
    assert http.calls == []


def test_unknown_command_is_a_usage_error():
    assert runner.invoke(cli, ["nope"]).exit_code == 2


def test_no_project_selected_exit_code_and_message():
    result = runner.invoke(cli, ["object-storage", "list-buckets"])
    assert result.exit_code == 6
    assert "No project selected" in result.output and "scaleinn configure" in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    "status,code", [(401, 3), (403, 4), (500, 7)]
)
def test_http_errors_map_to_exit_codes(http, logged_in, status, code):
    http.add(status, {"message": "nope"})
    result = runner.invoke(cli, ["object-storage", "list-buckets"])
    assert result.exit_code == code
    assert "Traceback" not in result.output


def test_network_failure_exit_code(http, logged_in):
    import requests

    http.add(exc=requests.exceptions.ConnectionError("down"))
    result = runner.invoke(cli, ["object-storage", "list-buckets"])
    assert result.exit_code == 5
    assert "Could not connect" in result.output


def test_not_logged_in_exit_code():
    cfg.update_config(project_id="p1")
    result = runner.invoke(cli, ["object-storage", "list-buckets"])
    assert result.exit_code == 6 and "not logged in" in result.output


def test_debug_logs_are_written_and_redacted(http, logged_in):
    http.add(200, [{"name": "b1"}])
    result = runner.invoke(cli, ["--debug", "object-storage", "list-buckets"])
    assert result.exit_code == 0
    log_text = cfg.log_path().read_text()
    for line in ("CLI initialized", "Initializing Object Storage module",
                 "Calling get-all-bucket API", "Backend response received: HTTP 200",
                 "Command completed"):
        assert line in log_text
    assert TEST_TOKEN not in log_text and TEST_TOKEN not in result.output


# ------------------------------------------------------------ formatting
ROWS = [{"name": "alpha", "size": 10, "public": True}, {"name": "b", "size": None, "extra": {"x": 1}}]


def test_format_table_unions_columns_and_aligns():
    table = format_table(ROWS)
    lines = table.splitlines()
    assert lines[0] == lines[2] == lines[-1]
    assert lines[0].startswith("+-") and "name" in lines[1] and "extra" in lines[1]
    assert "true" in table and '{"x":1}' in table
    assert len({len(line) for line in lines}) == 1  # every line same width


def test_format_table_explicit_columns():
    assert "size" not in format_table(ROWS, ["name"])


def test_format_json_roundtrip():
    assert json.loads(format_json({"a": [1, 2], "ü": "x"})) == {"a": [1, 2], "ü": "x"}


def test_extract_rows():
    assert extract_rows([{"a": 1}]) == [{"a": 1}]
    assert extract_rows({"status": "ok", "data": [{"a": 1}]}) == [{"a": 1}]
    assert extract_rows({"a": [{"x": 1}], "b": [{"y": 1}]}) is None  # ambiguous
    assert extract_rows({"status": "ok"}) is None
    assert extract_rows(["str"]) is None


def test_default_output_setting_is_honoured(http, logged_in):
    cfg.update_config(default_output="json")
    http.add(200, [{"name": "b1"}])
    result = split.invoke(cli, ["object-storage", "list-buckets"])
    assert json.loads(result.stdout) == [{"name": "b1"}]


# ---------------------------------------------------- log sanitization
@pytest.mark.parametrize(
    "text",
    [
        "Authorization: Bearer abc.def-ghi_123",
        "password=hunter2&x=1",
        '{"password": "has spaces in it", "ok": 1}',
        "{'access_token': 'abc123xyz'}",
        "refresh_token: r3fr3sh",
        '"refreshToken":"zzz999"',
    ],
)
def test_sanitize_redacts_credentials(text):
    cleaned = sanitize(text)
    for secret in ("abc.def-ghi_123", "hunter2", "has spaces", "abc123xyz", "r3fr3sh", "zzz999"):
        assert secret not in cleaned
    assert REDACTED in cleaned


def test_sanitize_masks_registered_secrets_anywhere():
    register_secret("opaque-secret-value")
    assert "opaque-secret-value" not in sanitize("something opaque-secret-value else")


def test_sanitize_does_not_mangle_the_http_security_warning():
    for message in cfg.connection_warnings(cfg.update_config(api_url="http://10.0.0.1:8080")):
        assert sanitize(message) == message


def test_sanitize_keeps_harmless_text():
    assert sanitize("GET /api/v1/x projectId=abc") == "GET /api/v1/x projectId=abc"
