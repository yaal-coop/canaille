import functools
import sys

import click
from canaille.backends import BaseBackend
from flask import current_app
from flask.cli import with_appcontext


def with_backendcontext(func):
    @functools.wraps(func)
    def _func(*args, **kwargs):
        if not current_app.config["TESTING"]:  # pragma: no cover
            with BaseBackend.get().session():
                result = func(*args, **kwargs)

        else:
            result = func(*args, **kwargs)

        return result

    return _func


@click.command()
@with_appcontext
@with_backendcontext
def check():
    """Check the configuration file."""
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
    """Installs canaille elements from the configuration."""
    from canaille.app.installation import install
    from canaille.app.configuration import ConfigurationException

    try:
        install(current_app.config)

    except ConfigurationException as exc:  # pragma: no cover
        print(exc)
        sys.exit(1)


def register(cli):
    cli.add_command(check)
    cli.add_command(install)
