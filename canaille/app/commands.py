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
@with_appcontext
@with_backendcontext
def check():
    """Test the configuration file.

    Attempt to reach the database and the SMTP server with the provided
    credentials.
    """
    from canaille.app.configuration import ConfigurationException
    from canaille.app.configuration import validate

    try:
        validate(current_app.config, validate_remote=True)
    except ConfigurationException as exc:
        print(exc)
        sys.exit(1)


@click.command()
@with_appcontext
def install():
    """Installs canaille elements from the configuration.

    For instance, depending on the configuration, this can generate OIDC
    keys or install LDAP schemas.
    """
    from canaille.app.configuration import ConfigurationException
    from canaille.app.installation import install

    try:
        install(current_app)

    except ConfigurationException as exc:  # pragma: no cover
        print(exc)
        sys.exit(1)


@click.command()
@with_appcontext
@click.option(
    "--path", default=None, type=click.Path(), help="The path to the config file"
)
def export_config(path: Path | None):
    """Export the configuration in TOML format.

    The configuration is exported to the file path passed by ``--path`` if set,
    or the :envvar:`CONFIG` environment variable if set, or a ``config.toml``
    file in the current directory.
    """
    from canaille.app.configuration import DEFAULT_CONFIG_FILE
    from canaille.app.configuration import export_config
    from canaille.app.configuration import settings_factory

    config_obj = settings_factory(
        current_app.config, all_options=True, init_with_examples=True
    )
    config_file = path or os.getenv("CONFIG", DEFAULT_CONFIG_FILE)
    export_config(config_obj, config_file)
    click.echo(f"Wrote configuration file at {config_file}")


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


def register(cli):
    cli.add_command(check)
    cli.add_command(install)
    cli.add_command(export_config)
    if HAS_HYPERCORN:  # pragma: no branch
        cli.add_command(run)
