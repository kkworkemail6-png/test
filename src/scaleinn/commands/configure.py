"""``scaleinn configure``: log in and select the active project."""

from __future__ import annotations

import click

from scaleinn.core import authentication, config as cfg, project_manager
from scaleinn.core.exceptions import (
    AuthenticationError,
    EndpointNotConfiguredError,
    ValidationError,
)
from scaleinn.core.logger import get_logger
from scaleinn.core.session import Session, pass_session
from scaleinn.utils import terminal

log = get_logger("configure")


def _apply_connection_options(session: Session, api_url, verify_ssl, ca_bundle) -> None:
    """Persist only the connection settings the user explicitly passed."""
    changes = {}
    if api_url is not None:
        changes["api_url"] = cfg.validate_api_url(api_url)
    if verify_ssl is not None:
        changes["verify_ssl"] = verify_ssl
    if ca_bundle is not None:
        changes["ca_bundle"] = ca_bundle
    if changes:
        cfg.update_config(**changes)
        session.reload()
        terminal.info("Connection settings saved.")


@click.command("configure", help="Sign in to Scaleinn and select the active project.")
@click.option("--api-url", help="Backend URL, e.g. https://app.scaleinn.in:8086 (http:// is also supported).")
@click.option("--verify-ssl/--no-verify-ssl", default=None, help="Enable/disable TLS certificate verification.")
@click.option(
    "--ca-bundle",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to a custom CA certificate bundle.",
)
@click.option("--project-only", is_flag=True, help="Only change the selected project, using the current login.")
@click.option(
    "--with-token",
    is_flag=True,
    help="Interim: supply an existing bearer token instead of logging in with a password.",
)
@pass_session
def configure(session: Session, api_url, verify_ssl, ca_bundle, project_only: bool, with_token: bool) -> None:
    terminal.info("Welcome to Scaleinn CLI\n")
    _apply_connection_options(session, api_url, verify_ssl, ca_bundle)
    for message in cfg.connection_warnings(session.config):
        terminal.warn_once(message)  # shown before any password is typed; not repeated later

    if project_only:
        if not session.token_manager.has_credentials:
            raise AuthenticationError(
                "You are not logged in.", hint="Run 'scaleinn configure' without --project-only."
            )
    else:
        auth_type = authentication.prompt_auth_type()
        terminal.info("")
        if with_token:
            token = click.prompt("Bearer access token", hide_input=True)
            authentication.store_bearer_token(session, token)
        else:
            identifier, password = authentication.prompt_credentials(auth_type)
            terminal.info("\nAuthenticating with Scaleinn...")
            authentication.authenticate(session, auth_type, identifier, password)
        cfg.update_config(auth_type=auth_type)
        session.reload()
        terminal.success("\nAuthentication successful!")

    terminal.info("\nFetching accessible projects...\n")
    try:
        projects = project_manager.fetch_projects(session.client, session.config)
    except EndpointNotConfiguredError as exc:
        terminal.warn(exc.message)
        terminal.info("Enter the project details manually.\n")
        project = project_manager.prompt_project_manually()
    else:
        if not projects:
            raise ValidationError(
                "No accessible projects were returned for this user.",
                hint="Ask your Scaleinn administrator for access to a project.",
            )
        project = project_manager.choose_project(projects)

    project_manager.save_selected_project(project)
    session.reload()
    terminal.success("\nProject selected successfully!")
    terminal.info(f"Selected project: {project.name}")
    terminal.info(f"Project ID: {project.id}")
    terminal.info("\nScaleinn CLI configuration completed.")
