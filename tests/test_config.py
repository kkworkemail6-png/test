import json
import os
import stat

import pytest

from scaleinn.core import config as cfg
from scaleinn.core.exceptions import ConfigurationError


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def test_defaults_when_no_file_exists():
    config = cfg.load_config()
    assert config["api_url"] == "https://app.scaleinn.in:8086"
    assert config["protocol"] == "https"
    assert config["default_output"] == "table"
    assert config["verify_ssl"] is True
    assert config["project_id"] is None


def test_config_dir_and_file_permissions():
    cfg.update_config(project_id="abc", project_name="Prod")
    assert mode(cfg.config_dir()) == 0o700
    assert mode(cfg.config_path()) == 0o600


def test_update_changes_only_given_keys_and_preserves_unknown_keys():
    cfg.update_config(auth_type="iam", project_id="p1", project_name="One")
    raw = json.loads(cfg.config_path().read_text())
    raw["endpoints"] = {"ct_list": "/x"}
    cfg.config_path().write_text(json.dumps(raw))

    cfg.update_config(project_id="p2", project_name="Two")
    after = json.loads(cfg.config_path().read_text())
    assert after["auth_type"] == "iam"  # untouched
    assert after["project_id"] == "p2"
    assert after["endpoints"] == {"ct_list": "/x"}  # unknown key preserved


def test_no_temp_files_left_after_write():
    cfg.update_config(project_id="p1")
    leftovers = [p.name for p in cfg.config_dir().iterdir() if p.name.endswith(".tmp")]
    assert leftovers == []


@pytest.mark.parametrize(
    "url,protocol",
    [("https://app.scaleinn.in:8086", "https"), ("http://192.168.192.234:8080/", "http")],
)
def test_http_and_https_endpoints_supported(url, protocol):
    config = cfg.update_config(api_url=url)
    assert config["protocol"] == protocol
    assert not config["api_url"].endswith("/")
    assert json.loads(cfg.config_path().read_text())["protocol"] == protocol


@pytest.mark.parametrize("bad", ["", "ftp://x", "app.scaleinn.in", "https://"])
def test_invalid_api_url_rejected(bad):
    with pytest.raises(ConfigurationError):
        cfg.update_config(api_url=bad)


def test_invalid_json_gives_clean_error():
    cfg.ensure_config_dir()
    cfg.config_path().write_text("{not json")
    with pytest.raises(ConfigurationError):
        cfg.load_config()


def test_connection_warnings():
    assert cfg.connection_warnings(cfg.update_config(api_url="http://10.0.0.1:8080"))
    assert cfg.connection_warnings(cfg.update_config(api_url="https://x.example", verify_ssl=False))
    assert cfg.connection_warnings(cfg.update_config(api_url="https://x.example", verify_ssl=True)) == []


def test_get_endpoint_normalizes_leading_slash():
    assert cfg.get_endpoint({"endpoints": {"a": "api/x"}}, "a") == "/api/x"
    assert cfg.get_endpoint({}, "a") is None
    assert cfg.get_endpoint({}, "a", "/d") == "/d"


def test_config_never_contains_secrets():
    cfg.update_config(auth_type="root", project_id="p")
    text = cfg.config_path().read_text().lower()
    assert "password" not in text and "token" not in text
