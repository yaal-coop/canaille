import sys

import click
from canaille import create_app
from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Token
from flask import current_app
from flask.cli import FlaskGroup
from flask.cli import with_appcontext


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command()
@with_appcontext
def clean():
    """
    Remove expired tokens and authorization codes.
    """
    from canaille.ldap_backend.backend import (
        setup_backend,
        teardown_backend,
    )

    if not current_app.config["TESTING"]:  # pragma: no cover
        setup_backend(current_app)

    for t in Token.all():
        if t.is_expired():
            t.delete()

    for a in AuthorizationCode.all():
        if a.is_expired():
            a.delete()

    if not current_app.config["TESTING"]:  # pragma: no cover
        teardown_backend(current_app)


@cli.command()
@with_appcontext
def check():
    """
    Check the configuration file.
    """
    from canaille.configuration import validate, ConfigurationException

    try:
        validate(current_app.config, validate_remote=True)
    except ConfigurationException as exc:
        print(exc)
        sys.exit(1)


@cli.command()
@with_appcontext
def install():
    """
    Installs canaille elements from the configuration.
    """
    from canaille.installation import install
    from canaille.configuration import ConfigurationException

    try:
        install(current_app.config)

    except ConfigurationException as exc:  # pragma: no cover
        print(exc)
        sys.exit(1)
