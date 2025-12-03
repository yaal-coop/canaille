import enum
import json
from datetime import timedelta

import click
import tomlkit
from flask import current_app
from flask.cli import with_appcontext
from joserfc.jwk import ECKey
from joserfc.jwk import OctKey
from joserfc.jwk import OKPKey
from joserfc.jwk import RSAKey

from canaille.app import models
from canaille.app.commands import with_backendcontext
from canaille.backends import Backend

from .jose import build_client_management_token


@click.command()
@with_appcontext
@with_backendcontext
def clean():
    """Remove expired tokens and authorization codes."""
    for t in Backend.instance.query(models.Token):
        if t.is_expired():
            Backend.instance.delete(t)

    for a in Backend.instance.query(models.AuthorizationCode):
        if a.is_expired():
            Backend.instance.delete(a)


@click.group()
def jwk():
    """JSON Web Key management."""
    pass


@jwk.group()
def create():
    """JSON Web Key creation."""
    pass

class OutputFormat(enum.Enum):
    JSON = enum.auto()
    TOML = enum.auto()

def _print_key(key, format: OutputFormat):
    """Print key with the selected output format."""
    if format == OutputFormat.JSON:
        click.echo(json.dumps(key.as_dict()))
    elif format == OutputFormat.TOML:
        key_as_table = tomlkit.inline_table()
        key_as_table.update(key.as_dict())
        click.echo(key_as_table.as_string())


@create.command()
@click.option("--size", default=2048, type=int, help="The key size")
@click.option("--format", type=click.Choice(OutputFormat, case_sensitive=False), default=OutputFormat.JSON, help="Output format")
def rsa(size: int, format: OutputFormat):
    """Create a RSA JSON Web Key."""
    key = RSAKey.generate_key(size, auto_kid=True)
    _print_key(key, format)


@create.command()
@click.option("--size", default=256, type=int, help="The key size")
@click.option("--format", type=click.Choice(OutputFormat, case_sensitive=False), default=OutputFormat.JSON, help="Output format")
def oct(size: int, format: OutputFormat):
    """Create a Oct JSON Web Key."""
    key = OctKey.generate_key(size, auto_kid=True)
    _print_key(key, format)


@create.command()
@click.option("--crv", default="P-256", type=str, help="The key CRV")
@click.option("--format", type=click.Choice(OutputFormat, case_sensitive=False), default=OutputFormat.JSON, help="Output format")
def ec(crv: str, format: OutputFormat):
    """Create a EC JSON Web Key."""
    key = ECKey.generate_key(crv, auto_kid=True)
    _print_key(key, format)


@create.command()
@click.option("--crv", default="Ed25519", type=str, help="The key CRV")
@click.option("--format", type=click.Choice(OutputFormat, case_sensitive=False), default=OutputFormat.JSON, help="Output format")
def okp(crv: str, format: OutputFormat):
    """Create a OKP JSON Web Key."""
    key = OKPKey.generate_key(crv, auto_kid=True)
    _print_key(key, format)


@click.group()
def jwt():
    """Client registration management."""
    pass


@jwt.command()
@click.option("--lifetime", default=86400, type=int, help="Token lifetime in seconds")
@with_appcontext
def registration(lifetime: int):
    """Generate a JWT token for dynamic client registration.

    Creates a JWT token with an auto-generated client_id that can be used
    to register a new OAuth2 client.
    """
    if not current_app.config["SERVER_NAME"]:
        raise click.ClickException(
            "You must define SERVER_NAME to issue tokens from the CLI"
        )

    token = build_client_management_token(
        "client:register", timedelta(seconds=lifetime)
    )
    click.echo(token)


@jwt.command()
@click.argument("client-id", required=True)
@click.option("--lifetime", default=86400, type=int, help="Token lifetime in seconds")
@with_appcontext
def management(client_id: str, lifetime: int):
    """Generate a JWT token for client management.

    Creates a JWT token that can be used to manage an existing OAuth2 client.
    """
    if not current_app.config["SERVER_NAME"]:
        raise click.ClickException(
            "You must define SERVER_NAME to issue tokens from the CLI"
        )

    token = build_client_management_token(
        "client:manage", timedelta(seconds=lifetime), client_id
    )
    click.echo(token)


def register(cli):
    cli.add_command(clean)
    cli.add_command(jwk)
    cli.add_command(jwt)
