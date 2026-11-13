"""Images category: one extra command layer above its services.

``scaleinn images --help`` lists the services below; each one is also registered as a
top-level command (see ``services/__init__.py``), so ``scaleinn marketplace-images --help``
works as well as ``scaleinn images marketplace-images --help``.

A category has no operations or models of its own: those live in each service.
"""

from __future__ import annotations

import click

from scaleinn.core.command_groups import OrderedGroup
from scaleinn.core.logger import get_logger
from scaleinn.services.images.marketplace_images.commands import marketplace_images
from scaleinn.services.images.project_images.commands import project_images

log = get_logger("images")

# In the order shown by ``scaleinn images --help``.
SUBMODULES = (marketplace_images, project_images,)


@click.group(
    "images",
    cls=OrderedGroup,
    short_help="Manage images: marketplace images and project images.",
    help="Manage images: marketplace images and project images.",
)
def images() -> None:
    log.info("Initializing Images module")


for _submodule in SUBMODULES:
    images.add_command(_submodule)
