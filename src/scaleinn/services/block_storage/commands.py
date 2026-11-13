"""Block Storage category: one extra command layer above its services.

``scaleinn block-storage --help`` lists the services below; each one is also registered as a
top-level command (see ``services/__init__.py``), so ``scaleinn network-storage --help``
works as well as ``scaleinn block-storage network-storage --help``.

A category has no operations or models of its own: those live in each service.
"""

from __future__ import annotations

import click

from scaleinn.core.command_groups import OrderedGroup
from scaleinn.core.logger import get_logger
from scaleinn.services.block_storage.additional_disks.commands import additional_disks
from scaleinn.services.block_storage.network_storage.commands import network_storage
from scaleinn.services.block_storage.os_disks.commands import os_disks
from scaleinn.services.block_storage.snapshot.commands import snapshot

log = get_logger("block_storage")

# In the order shown by ``scaleinn block-storage --help``.
SUBMODULES = (network_storage, additional_disks, snapshot, os_disks,)


@click.group(
    "block-storage",
    cls=OrderedGroup,
    short_help="Manage block storage: network storage, additional disks, snapshots and OS disks.",
    help="Manage block storage: network storage, additional disks, snapshots and OS disks.",
)
def block_storage() -> None:
    log.info("Initializing Block Storage module")


for _submodule in SUBMODULES:
    block_storage.add_command(_submodule)
