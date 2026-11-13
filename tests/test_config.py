import json
import os
import stat

import pytest

from scaleinn.core import config as cfg
from scaleinn.core import env
from scaleinn.core.exceptions import ConfigurationError


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def test_defaults_when_no_file_exists():
    config = cfg.load_config()
    assert config["api_url"] == "https://app.scaleinn.in:8443"
    assert config["object_storage_url"] == "https://app.scaleinn.in:8086"  # its own URL
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


@pytest.mark.parametrize("url", ["https://app.scaleinn.in:8443/", "http://192.168.192.234:8080/"])
def test_url_overrides_are_cleaned_and_stored_for_http_and_https(url):
    config = cfg.update_config(api_url=url, object_storage_url=url)
    assert config["api_url"] == url.rstrip("/") == config["object_storage_url"]
    stored = json.loads(cfg.config_path().read_text())
    assert stored["api_url"] == url.rstrip("/")


def test_environment_urls_are_not_pinned_into_config_json():
    cfg.update_config(project_id="p1")
    stored = json.loads(cfg.config_path().read_text())
    assert stored["api_url"] is None and stored["object_storage_url"] is None  # "use env.py"
    assert stored["protocol"] == "https"


def test_protocol_selects_the_matching_environment_block():
    https = cfg.update_config(protocol="https")
    http = cfg.update_config(protocol="http")
    assert (https["api_url"], https["object_storage_url"]) == (
        env.HTTPS["apiUrl"], env.HTTPS["objectStorageUrl"])
    assert (http["api_url"], http["object_storage_url"]) == (
        env.HTTP["apiUrl"], env.HTTP["objectStorageUrl"])
    assert http["api_url"].startswith("http://") and https["api_url"].startswith("https://")


def test_override_wins_over_environment_for_that_service_only():
    config = cfg.update_config(api_url="https://other.example:9999")
    assert config["api_url"] == "https://other.example:9999"
    assert config["object_storage_url"] == env.HTTPS["objectStorageUrl"]


def test_invalid_protocol_rejected():
    with pytest.raises(ConfigurationError):
        cfg.update_config(protocol="ftp")


def test_service_url_lookup():
    config = cfg.load_config()
    assert cfg.service_url(config) == config["api_url"]  # default service
    assert cfg.service_url(config, "object_storage") == config["object_storage_url"]
    with pytest.raises(ConfigurationError):
        cfg.service_url(config, "nope")


@pytest.mark.parametrize("bad", ["ftp://x", "app.scaleinn.in", "https://"])
def test_invalid_api_url_rejected(bad):
    with pytest.raises(ConfigurationError):
        cfg.update_config(api_url=bad)


def test_invalid_json_gives_clean_error():
    cfg.ensure_config_dir()
    cfg.config_path().write_text("{not json")
    with pytest.raises(ConfigurationError):
        cfg.load_config()


def test_http_warning_covers_every_service_url():
    only_object_storage_http = cfg.update_config(
        api_url="https://x.example", object_storage_url="http://10.0.0.1:9000")
    assert any("plain HTTP" in w for w in cfg.connection_warnings(only_object_storage_http))


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
