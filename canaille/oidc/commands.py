import json

import click
from flask.cli import with_appcontext
from joserfc.jwk import ECKey
from joserfc.jwk import OctKey
from joserfc.jwk import OKPKey
from joserfc.jwk import RSAKey

from canaille.app import models
from canaille.app.commands import with_backendcontext
from canaille.backends import Backend


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


@create.command()
@click.option("--size", default=2048, type=int, help="The key size")
def rsa(size: int):
    """Create a RSA JSON Web Key."""
    key = RSAKey.generate_key(size, auto_kid=True)
    click.echo(json.dumps(key.as_dict()))


@create.command()
@click.option("--size", default=256, type=int, help="The key size")
def oct(size: int):
    """Create a Oct JSON Web Key."""
    key = OctKey.generate_key(size, auto_kid=True)
    click.echo(json.dumps(key.as_dict()))


@create.command()
@click.option("--crv", default="P-256", type=str, help="The key CRV")
def ec(crv: str):
    """Create a EC JSON Web Key."""
    key = ECKey.generate_key(crv, auto_kid=True)
    click.echo(json.dumps(key.as_dict()))


@create.command()
@click.option("--crv", default="Ed25519", type=str, help="The key CRV")
def okp(crv: str):
    """Create a OKP JSON Web Key."""
    key = OKPKey.generate_key(crv, auto_kid=True)
    click.echo(json.dumps(key.as_dict()))


def register(cli):
    cli.add_command(clean)
    cli.add_command(jwk)
