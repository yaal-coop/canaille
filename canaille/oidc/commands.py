import click
from flask.cli import with_appcontext

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


def register(cli):
    cli.add_command(clean)
