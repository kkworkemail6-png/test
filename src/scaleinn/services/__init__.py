"""Resource modules.

Layout::

    services/<name>/{commands,operations,models}.py              a service
    services/<category>/commands.py                              an extra layer that groups services
    services/<category>/<name>/{commands,operations,models}.py   a service inside a category

Every service is reachable as its own top-level command (``scaleinn cloud-dns``),
and categories also expose their services one level down
(``scaleinn network cloud-dns``).

To add a service: create its package, write a Click group in ``commands.py`` and add
it to the matching section in :func:`register_services`.
"""

from __future__ import annotations

import click


def register_services(root: click.Group) -> None:
    """Add every service to ``root`` and list them in titled ``--help`` sections."""
    from scaleinn.services.block_storage.commands import SUBMODULES as BLOCK_STORAGE_SERVICES
    from scaleinn.services.block_storage.commands import block_storage
    from scaleinn.services.ct.commands import ct
    from scaleinn.services.ice.commands import ice
    from scaleinn.services.images.commands import SUBMODULES as IMAGE_SERVICES
    from scaleinn.services.images.commands import images
    from scaleinn.services.managed_services.commands import SUBMODULES as MANAGED_SERVICES
    from scaleinn.services.managed_services.commands import managed_services
    from scaleinn.services.network.commands import SUBMODULES as NETWORK_SERVICES
    from scaleinn.services.network.commands import network
    from scaleinn.services.object_storage.commands import object_storage

    root.add_section("Compute", ice, ct)
    root.add_section("Network", network, *NETWORK_SERVICES)
    root.add_section("Storage", object_storage, block_storage, *BLOCK_STORAGE_SERVICES)
    root.add_section("Images", images, *IMAGE_SERVICES)
    root.add_section("Managed Services", managed_services, *MANAGED_SERVICES)
