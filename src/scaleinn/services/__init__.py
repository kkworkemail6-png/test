"""Resource modules.

To add a service: create ``services/<name>/{commands,operations,models}.py`` with
a Click group in ``commands.py`` and add one line to :func:`register_services`.
"""

from __future__ import annotations

import click


def register_services(root: click.Group) -> None:
    from scaleinn.services.ct.commands import ct
    from scaleinn.services.object_storage.commands import object_storage

    root.add_command(object_storage)
    root.add_command(ct)
