"""Management category: one extra command layer above its services.

``scaleinn management --help`` lists the services below; each one is also registered as a
top-level command (see ``services/__init__.py``), so ``scaleinn users --help``
works as well as ``scaleinn management users --help``.

A category has no operations or models of its own: those live in each service.
"""

from __future__ import annotations

import click

from scaleinn.core.command_groups import OrderedGroup
from scaleinn.core.logger import get_logger
from scaleinn.services.management.groups.commands import groups
from scaleinn.services.management.organizations.commands import organizations
from scaleinn.services.management.policies.commands import policies
from scaleinn.services.management.projects.commands import projects
from scaleinn.services.management.secret_manager.commands import secret_manager
from scaleinn.services.management.users.commands import users

log = get_logger("management")

# In the order shown by ``scaleinn management --help``.
SUBMODULES = (users, secret_manager, groups, organizations, policies, projects,)


@click.group(
    "management",
    cls=OrderedGroup,
    short_help="Manage users, secrets, groups, organizations, policies and projects.",
    help="Manage users, secrets, groups, organizations, policies and projects.",
)
def management() -> None:
    log.info("Initializing Management module")


for _submodule in SUBMODULES:
    management.add_command(_submodule)
