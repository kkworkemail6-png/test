import json

from click.testing import CliRunner

from scaleinn.cli import cli
from scaleinn.core import config as cfg

from conftest import TEST_PROJECT, split_runner

runner = CliRunner()
split = split_runner()


def test_ct_group_and_list_command_are_registered():
    assert cli.commands["ct"].commands["list"] is not None
    result = runner.invoke(cli, ["ct", "--help"])
    assert result.exit_code == 0 and "list" in result.output


def test_ct_list_does_not_invent_an_endpoint(http, logged_in):
    result = runner.invoke(cli, ["ct", "list"])
    assert result.exit_code == 6
    assert "endpoints.ct_list" in result.output
    assert http.calls == []  # nothing was sent anywhere


def test_ct_list_uses_configured_endpoint(http, logged_in):
    cfg.update_config(endpoints={"ct_list": "/api/v1/ct/list"})
    http.add(200, [{"name": "ct-1"}])
    result = split.invoke(cli, ["ct", "list", "--output", "json"])
    assert result.exit_code == 0, result.output
    call = http.calls[0]
    assert call["url"].endswith("/api/v1/ct/list")
    assert call["params"] == {"projectId": TEST_PROJECT}
    assert json.loads(result.stdout) == [{"name": "ct-1"}]
