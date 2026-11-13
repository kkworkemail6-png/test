"""The environment module: separate http / https settings and per-service URLs."""

import pytest

from scaleinn.core import env


def test_https_and_http_blocks_are_separate_and_use_the_right_scheme():
    assert set(env.ENVIRONMENTS) == {"https", "http"}
    for key in ("apiUrl", "objectStorageUrl"):
        assert env.HTTPS[key].startswith("https://")
        assert env.HTTP[key].startswith("http://")


def test_documented_https_urls():
    assert env.HTTPS["apiUrl"] == "https://app.scaleinn.in:8443"
    assert env.HTTPS["objectStorageUrl"] == "https://app.scaleinn.in:8086"


def test_object_storage_has_its_own_url():
    assert env.HTTPS["apiUrl"] != env.HTTPS["objectStorageUrl"]


@pytest.mark.parametrize("protocol", ["http", "https"])
def test_backup_option_value_is_available_for_later_apis(protocol):
    assert env.get_value(protocol, "backupOptionValue") == "backup-store"
    assert env.BACKUP_OPTION_VALUE == "backup-store"


def test_get_value_default_and_copy_semantics():
    assert env.get_value("https", "missing", "fallback") == "fallback"
    block = env.get_environment("https")
    block["apiUrl"] = "changed"
    assert env.HTTPS["apiUrl"] == "https://app.scaleinn.in:8443"  # the module data is untouched


def test_default_protocol_is_https():
    assert env.DEFAULT_PROTOCOL == "https"
