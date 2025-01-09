import importlib.metadata

import click
from flask.cli import FlaskGroup

import canaille.app.commands
import canaille.backends.commands
import canaille.core.commands
import canaille.oidc.commands
from canaille import create_app

version = importlib.metadata.version("canaille")


def create_cli_app():  # pragma: no cover
    # Force the non-application of migrations
    return create_app(init_backend=False)


@click.group(
    cls=FlaskGroup,
    create_app=create_cli_app,
    add_version_option=False,
    add_default_commands=False,
)
@click.version_option(version, prog_name="Canaille")
def cli():
    """Canaille management utilities."""


canaille.app.commands.register(cli)
canaille.backends.commands.register(cli)
canaille.core.commands.register(cli)
canaille.oidc.commands.register(cli)


if __name__ == "__main__":  # pragma: no cover
    cli()
