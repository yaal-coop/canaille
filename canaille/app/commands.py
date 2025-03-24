import functools
import os
import sys
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext

from canaille.backends import Backend

try:
    import hypercorn  # noqa: F401

    HAS_HYPERCORN = True
except ImportError:  # pragma: no cover
    HAS_HYPERCORN = False


def with_backendcontext(func):
    @functools.wraps(func)
    def _func(*args, **kwargs):
        if not current_app.config["TESTING"]:  # pragma: no cover
            with Backend.instance.session():
                result = func(*args, **kwargs)

        else:
            result = func(*args, **kwargs)

        return result

    return _func


@click.command()
@click.pass_context
@with_appcontext
def install(ctx):
    """Installs canaille elements from the configuration.

    For instance, depending on the configuration, this can generate OIDC
    keys or install LDAP schemas.
    """
    from canaille.app.installation import install

    app = ctx.obj.load_app()
    install(app)


if HAS_HYPERCORN:  # pragma: no cover

    @click.command()
    @with_appcontext
    @click.option(
        "--config",
        default=None,
        help="Path to a TOML hypercorn configuration file.",
        type=click.Path(),
    )
    def run(config: str | None):
        """Run Canaille in a hypercorn application server.

        Have a look at the :doc:`Hypercorn configuration documentation <hypercorn:how_to_guides/configuring>` to find how to configure it.
        """
        from hypercorn.config import Config
        from hypercorn.run import run as hypercorn_run

        config_obj = Config.from_toml(config) if config else Config()
        config_obj.application_path = "canaille.app.server:app"
        exitcode = hypercorn_run(config_obj)
        sys.exit(exitcode)


@click.group()
def config():
    """Handle Canaille configuration file."""
    pass


@config.command()
@with_appcontext
@click.option(
    "--path", default=None, type=click.Path(), help="The path to the config file"
)
def dump(path: Path | None):
    """Export the configuration in TOML format.

    The configuration is exported to the file path passed by ``--path`` if set,
    or the :envvar:`CONFIG` environment variable if set, or a ``config.toml``
    file in the current directory.
    """
    from canaille.app.configuration import DEFAULT_CONFIG_FILE
    from canaille.app.configuration import export_config
    from canaille.app.configuration import settings_factory

    config_obj = settings_factory(current_app.config, init_with_examples=True)
    config_file = path or os.getenv("CONFIG", DEFAULT_CONFIG_FILE)
    export_config(config_obj, config_file)
    click.echo(f"Wrote configuration file at {config_file}")


@config.command()
@with_appcontext
@with_backendcontext
def check():
    """Test the network connections defined in the configuration file.

    Attempt to reach the database and the SMTP server with the provided
    credentials.
    """
    from canaille.app.configuration import check_network_config

    success = True
    results = check_network_config(current_app.config)
    prefix = {
        True: click.style("OK", fg="green"),
        False: click.style("KO", fg="red"),
        None: click.style("--", fg="blue"),
    }
    for result in results:
        success = result.success is not False and success
        click.echo(prefix[result.success], nl=False)
        click.echo(" " + result.message)

    if not success:
        sys.exit(1)


def register(cli):
    cli.add_command(install)
    if HAS_HYPERCORN:  # pragma: no branch
        cli.add_command(run)
    cli.add_command(config)
