import click
from flask.cli import with_appcontext

from canaille.app import models
from canaille.app.commands import with_backendcontext
from canaille.backends import BaseBackend


@click.command()
@with_appcontext
@with_backendcontext
def clean():
    """Remove expired tokens and authorization codes."""
    for t in BaseBackend.instance.query(models.Token):
        if t.is_expired():
            t.delete()

    for a in BaseBackend.instance.query(models.AuthorizationCode):
        if a.is_expired():
            a.delete()


def register(cli):
    cli.add_command(clean)
