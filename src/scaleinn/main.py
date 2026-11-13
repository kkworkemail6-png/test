"""Console-script entry point (``scaleinn``)."""

from __future__ import annotations

from scaleinn.cli import cli


def main() -> None:
    cli(prog_name="scaleinn")


if __name__ == "__main__":
    main()
