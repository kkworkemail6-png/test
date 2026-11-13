import json
import os
import stat
from datetime import datetime, timedelta, timezone

import pytest

from scaleinn.core import config as cfg
from scaleinn.core import credentials
from scaleinn.core.exceptions import AuthenticationError, NotConfiguredError
from scaleinn.core.token_manager import TokenManager, make_token_record, parse_expiry


def test_credentials_file_has_600_and_dir_700():
    credentials.save_credentials(make_token_record("a-token", "r-token", expires_in=3600))
    assert stat.S_IMODE(os.stat(cfg.credentials_path()).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(cfg.config_dir()).st_mode) == 0o700


def test_only_token_fields_are_persisted_never_a_password():
    credentials.save_credentials(
        {"access_token": "a", "password": "hunter2", "username": "root", "refresh_token": "r"}
    )
    stored = json.loads(cfg.credentials_path().read_text())
    assert set(stored) == {"access_token", "refresh_token"}
    assert "hunter2" not in cfg.credentials_path().read_text()


def test_make_token_record_expiry_from_expires_in():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    record = make_token_record("a", expires_in=3600, now=now)
    assert parse_expiry(record["expires_at"]) == now + timedelta(hours=1)
    assert record["token_type"] == "Bearer"


def test_absolute_expiry_wins_over_expires_in():
    record = make_token_record("a", expires_in=10, expires_at="2030-01-01T00:00:00Z")
    assert parse_expiry(record["expires_at"]).year == 2030


@pytest.mark.parametrize("value", [None, "", "garbage"])
def test_unknown_expiry_is_not_treated_as_expired(value):
    credentials.save_credentials({"access_token": "a", "expires_at": value})
    assert TokenManager(cfg.load_config()).is_expired() is False


def test_expired_and_valid_tokens():
    past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    credentials.save_credentials({"access_token": "a", "expires_at": past})
    assert TokenManager(cfg.load_config()).is_expired() is True
    credentials.save_credentials({"access_token": "a", "expires_at": future})
    assert TokenManager(cfg.load_config()).is_expired() is False


def test_missing_credentials_raise_not_configured():
    manager = TokenManager(cfg.load_config())
    assert manager.has_credentials is False
    with pytest.raises(NotConfiguredError):
        manager.access_token


def test_store_then_read_back():
    manager = TokenManager(cfg.load_config())
    manager.store(make_token_record("tok-1", "ref-1"))
    assert manager.access_token == "tok-1"
    assert manager.refresh_token == "ref-1"


def test_refresh_replaces_tokens_and_keeps_old_refresh_if_not_rotated(http, make_client):
    cfg.update_config(endpoints={"refresh": "/auth/refresh"})
    credentials.save_credentials(make_token_record("old", "ref-1"))
    client = make_client()
    http.add(200, {"access_token": "new-access"})
    client._tokens.refresh(client)
    assert client._tokens.access_token == "new-access"
    assert client._tokens.refresh_token == "ref-1"
    assert http.calls[0]["url"].endswith("/auth/refresh")
    assert "Authorization" not in http.calls[0]["headers"]


def test_refresh_without_endpoint_asks_to_login_again(make_client):
    credentials.save_credentials(make_token_record("old", "ref-1"))
    client = make_client()
    assert client._tokens.can_refresh() is False
    with pytest.raises(AuthenticationError):
        client._tokens.refresh(client)
