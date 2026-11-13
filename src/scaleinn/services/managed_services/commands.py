"""Managed Services category: one extra command layer above its services.

``scaleinn managed-services --help`` lists the services below; each one is also registered as a
top-level command (see ``services/__init__.py``), so ``scaleinn database --help``
works as well as ``scaleinn managed-services database --help``.

A category has no operations or models of its own: those live in each service.
"""

from __future__ import annotations

import click

from scaleinn.core.command_groups import OrderedGroup
from scaleinn.core.logger import get_logger
from scaleinn.services.managed_services.alert_manager.commands import alert_manager
from scaleinn.services.managed_services.database.commands import database
from scaleinn.services.managed_services.docker.commands import docker
from scaleinn.services.managed_services.load_balancer.commands import load_balancer
from scaleinn.services.managed_services.vps.commands import vps
from scaleinn.services.managed_services.waf.commands import waf

log = get_logger("managed_services")

# In the order shown by ``scaleinn managed-services --help``.
SUBMODULES = (database, docker, load_balancer, waf, vps, alert_manager,)


@click.group(
    "managed-services",
    cls=OrderedGroup,
    short_help="Managed services: Database as a Service, Docker as a Service, Load Balancer, WAF, VPS and Alert Manager.",
    help="Managed services: Database as a Service, Docker as a Service, Load Balancer, WAF, VPS and Alert Manager.",
)
def managed_services() -> None:
    log.info("Initializing Managed Services module")


for _submodule in SUBMODULES:
    managed_services.add_command(_submodule)
