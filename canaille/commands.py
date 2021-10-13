import click
import sys

from canaille import create_app
from canaille.models import AuthorizationCode, Token
from flask import current_app
from flask.cli import with_appcontext, FlaskGroup


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command()
@with_appcontext
def clean():
    """
    Remove expired tokens and authorization codes.
    """
    from canaille import setup_ldap_connection, teardown_ldap_connection

    setup_ldap_connection(current_app)

    for t in Token.filter():
        if t.is_expired():
            t.delete()

    for a in AuthorizationCode.filter():
        if a.is_expired():
            a.delete()

    teardown_ldap_connection(current_app)


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
