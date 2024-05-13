import click
from flask.cli import FlaskGroup

import canaille.app.commands
import canaille.backends.commands
import canaille.core.commands
import canaille.oidc.commands
from canaille import create_app


@click.group(
    cls=FlaskGroup,
    create_app=create_app,
    add_version_option=False,
    add_default_commands=False,
)
def cli():
    """Canaille management utilities."""


canaille.app.commands.register(cli)
canaille.backends.commands.register(cli)
canaille.core.commands.register(cli)
canaille.oidc.commands.register(cli)
