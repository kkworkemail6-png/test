"""Network category: one extra command layer above its services.

``scaleinn network --help`` lists the services below; each one is also registered as a
top-level command (see ``services/__init__.py``), so ``scaleinn vpc --help``
works as well as ``scaleinn network vpc --help``.

A category has no operations or models of its own: those live in each service.
"""

from __future__ import annotations

import click

from scaleinn.core.command_groups import OrderedGroup
from scaleinn.core.logger import get_logger
from scaleinn.services.network.cloud_dns.commands import cloud_dns
from scaleinn.services.network.ipam.commands import ipam
from scaleinn.services.network.reserved_ip.commands import reserved_ip
from scaleinn.services.network.router.commands import router
from scaleinn.services.network.security_group.commands import security_group
from scaleinn.services.network.shared_vpc.commands import shared_vpc
from scaleinn.services.network.vpc.commands import vpc

log = get_logger("network")

# In the order shown by ``scaleinn network --help``.
SUBMODULES = (vpc, shared_vpc, ipam, router, security_group, reserved_ip, cloud_dns,)


@click.group(
    "network",
    cls=OrderedGroup,
    short_help="Manage networking: VPC, Shared VPC, IPAM, routers, security groups, reserved IPs and Cloud DNS.",
    help="Manage networking: VPC, Shared VPC, IPAM, routers, security groups, reserved IPs and Cloud DNS.",
)
def network() -> None:
    log.info("Initializing Network module")


for _submodule in SUBMODULES:
    network.add_command(_submodule)
