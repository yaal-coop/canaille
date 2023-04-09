import canaille.app.commands
import canaille.core.commands
import canaille.oidc.commands
import click
from canaille import create_app
from flask.cli import FlaskGroup


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass  # pragma: no cover


canaille.app.commands.register(cli)
canaille.core.commands.register(cli)
canaille.oidc.commands.register(cli)
