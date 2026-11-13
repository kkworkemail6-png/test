"""Interactive authentication flow used by ``scaleinn configure``.

Collects credentials securely (the password prompt does not echo), calls the
login dispatcher in :mod:`scaleinn.auth.login`, and stores only the resulting
tokens. Passwords are never written to disk or logs.
"""

from __future__ import annotations

import click

from scaleinn.auth import iam_auth, login as login_module, root_auth
from scaleinn.core.logger import register_secret
from scaleinn.core.session import Session
from scaleinn.core.token_manager import make_token_record

AUTH_CHOICES = {1: "root", 2: "iam"}


def prompt_auth_type() -> str:
    click.echo("Select authentication type:\n")
    click.echo("1. Root User")
    click.echo("2. IAM User\n")
    choice = click.prompt("Enter your choice", type=click.IntRange(1, 2))
    return AUTH_CHOICES[choice]


def prompt_credentials(auth_type: str) -> tuple[str, str]:
    label = root_auth.IDENTIFIER_LABEL if auth_type == "root" else iam_auth.IDENTIFIER_LABEL
    identifier = click.prompt(label).strip()
    password = click.prompt("Password", hide_input=True)
    register_secret(password)  # defense in depth: mask it if it ever reaches a log line
    return identifier, password


def authenticate(session: Session, auth_type: str, identifier: str, password: str) -> None:
    """Log in with the backend and persist the returned tokens."""
    record = login_module.login(session.client, session.config, auth_type, identifier, password)
    session.token_manager.store(record)


def store_bearer_token(session: Session, token: str) -> None:
    """Store an existing bearer token (interim alternative to password login)."""
    register_secret(token)
    session.token_manager.store(make_token_record(access_token=token.strip()))
