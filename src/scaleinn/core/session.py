"""Per-invocation context shared by every command.

A :class:`Session` is created once by the top-level CLI group and handed to
commands through ``@pass_session``. Everything is built lazily so that
``scaleinn --help`` and ``scaleinn --version`` never touch the config files or
the network.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any

import click

from scaleinn.core import config as cfg
from scaleinn.core import credentials
from scaleinn.core.api_client import ApiClient
from scaleinn.core.logger import get_logger
from scaleinn.core.project_manager import get_selected_project_id
from scaleinn.core.token_manager import TokenManager

log = get_logger("session")


class Session:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug

    @cached_property
    def config(self) -> dict[str, Any]:
        log.info("Loading configuration")
        return cfg.load_config()

    @cached_property
    def token_manager(self) -> TokenManager:
        return TokenManager(self.config)

    @cached_property
    def client(self) -> ApiClient:
        return ApiClient(self.config, self.token_manager)

    @property
    def project_id(self) -> str:
        """The locally selected project (the backend still enforces access)."""
        project_id = get_selected_project_id(self.config)
        log.info("Project selected: %s", project_id)
        return project_id

    @property
    def organisation(self) -> dict[str, Any] | None:
        """The organisation selected in ``scaleinn configure`` (``{"id", "name"}``) or ``None``."""
        return credentials.get_organisation()

    @property
    def policies(self) -> Any:
        """The user's policies stored by the last ``scaleinn configure`` (``None`` if none)."""
        return credentials.get_policies()

    @property
    def default_output(self) -> str:
        return self.config["default_output"]

    def reload(self) -> None:
        """Drop cached state after configuration was changed on disk."""
        for name in ("config", "token_manager", "client"):
            self.__dict__.pop(name, None)


pass_session = click.make_pass_decorator(Session)
