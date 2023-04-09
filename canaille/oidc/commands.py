import click
from canaille.app.commands import with_backendcontext
from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Token
from flask.cli import with_appcontext


@click.command()
@with_appcontext
@with_backendcontext
def clean():
    """
    Remove expired tokens and authorization codes.
    """
    for t in Token.query():
        if t.is_expired():
            t.delete()

    for a in AuthorizationCode.query():
        if a.is_expired():
            a.delete()


def register(cli):
    cli.add_command(clean)
