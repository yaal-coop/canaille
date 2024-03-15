import click
from flask.cli import FlaskGroup

import canaille.app.commands
import canaille.core.commands
import canaille.oidc.commands
from canaille import create_app


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass  # pragma: no cover


canaille.app.commands.register(cli)
canaille.core.commands.register(cli)
canaille.oidc.commands.register(cli)
