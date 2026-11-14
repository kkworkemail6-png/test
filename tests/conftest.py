"""Shared fixtures: isolated config dir, fake HTTP layer, logged-in state.

No test talks to a real network or needs real Scaleinn credentials.
"""

from __future__ import annotations

import json
import logging

import pytest
import requests

from scaleinn.core import config as cfg
from scaleinn.core import credentials
from scaleinn.core.api_client import ApiClient
from scaleinn.core.logger import clear_secrets
from scaleinn.core.token_manager import TokenManager, make_token_record
from scaleinn.utils import terminal

TEST_TOKEN = "tok_SECRET_abc123XYZ"
TEST_REFRESH = "ref_SECRET_def456UVW"
TEST_PROJECT = "proj1234ab"


def split_runner():
    """CliRunner whose ``.stdout`` / ``.stderr`` are separate on every Click version.

    Click <= 8.1 mixes stderr into stdout by default; Click >= 8.2 removed the
    ``mix_stderr`` argument and always separates them.
    """
    from click.testing import CliRunner

    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


class FakeResponse:
    def __init__(self, status_code=200, json_body=None, text=None, reason="OK"):
        self.status_code = status_code
        self.reason = reason
        if text is not None:
            self.text = text
        elif json_body is not None:
            self.text = json.dumps(json_body)
        else:
            self.text = ""
        self.content = self.text.encode()
        self._json = json_body

    def json(self):
        if self._json is not None:
            return self._json
        return json.loads(self.text)  # raises ValueError for non-JSON


class FakeHttp:
    """Replaces ``requests.Session.request``; records calls, replays queued replies."""

    def __init__(self):
        self.calls: list[dict] = []
        self._queue: list = []

    def add(self, status=200, json_body=None, text=None, exc=None):
        self._queue.append(exc if exc is not None else FakeResponse(status, json_body, text))
        return self

    def __call__(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        if not self._queue:
            raise AssertionError(f"Unexpected HTTP call in test: {method} {url}")
        item = self._queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Point ~/.scaleinn at a temp dir and clean up logging between tests."""
    monkeypatch.setenv(cfg.CONFIG_DIR_ENV, str(tmp_path / ".scaleinn"))
    terminal.reset_warnings()
    yield tmp_path / ".scaleinn"
    logger = logging.getLogger("scaleinn")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    clear_secrets()


@pytest.fixture
def http(monkeypatch):
    fake = FakeHttp()
    monkeypatch.setattr(requests.Session, "request", fake)
    return fake


@pytest.fixture
def logged_in():
    """A configured user: tokens, organisation and project stored in credentials.json."""
    credentials.save_credentials(make_token_record(TEST_TOKEN, refresh_token=TEST_REFRESH))
    credentials.update_context(
        organisation=credentials.selection("org-1", "Acme"),
        project=credentials.selection(TEST_PROJECT, "Production"),
    )
    cfg.update_config(auth_type="root")


@pytest.fixture
def make_client():
    def factory(**config_changes):
        if config_changes:
            cfg.update_config(**config_changes)
        config = cfg.load_config()
        return ApiClient(config, TokenManager(config), warn=False)

    return factory
