import click
from canaille.app import models
from canaille.app.commands import with_backendcontext
from flask.cli import with_appcontext


@click.command()
@with_appcontext
@with_backendcontext
def clean():
    """Remove expired tokens and authorization codes."""
    for t in models.Token.query():
        if t.is_expired():
            t.delete()

    for a in models.AuthorizationCode.query():
        if a.is_expired():
            a.delete()


def register(cli):
    cli.add_command(clean)
