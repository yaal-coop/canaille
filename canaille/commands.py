import functools
import sys

import click
from canaille import create_app
from canaille.models import Group
from canaille.models import User
from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Token
from canaille.populate import fake_groups
from canaille.populate import fake_users
from flask import current_app
from flask.cli import FlaskGroup
from flask.cli import with_appcontext

try:
    import faker

    HAS_FAKER = True
except ImportError:  # pragma: no cover
    HAS_FAKER = False


def with_backendcontext(func):
    @functools.wraps(func)
    def _func(*args, **kwargs):
        from canaille.ldap_backend.backend import (
            setup_backend,
            teardown_backend,
        )

        if not current_app.config["TESTING"]:  # pragma: no cover
            setup_backend(current_app)

        result = func(*args, **kwargs)

        if not current_app.config["TESTING"]:  # pragma: no cover
            teardown_backend(current_app)

        return result

    return _func


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    pass


@cli.command()
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


if HAS_FAKER:  # pragma: no branch

    @cli.group()
    @click.option("--nb", default=1, help="Number of items to create")
    @click.pass_context
    @with_appcontext
    def populate(ctx, nb):
        """
        Populate the database with generated random data.
        """
        ctx.ensure_object(dict)

        ctx.obj["number"] = nb

    @populate.command()
    @click.pass_context
    @with_appcontext
    @with_backendcontext
    def users(ctx):
        """
        Populate the database with generated random users.
        """

        fake_users(ctx.obj["number"])

    @populate.command()
    @click.pass_context
    @click.option(
        "--nb-users-max",
        default=1,
        help="The maximum number of users that will randomly be affected in the group",
    )
    @with_appcontext
    @with_backendcontext
    def groups(ctx, nb_users_max):
        """
        Populate the database with generated random groups.
        """

        fake_groups(ctx.obj["number"], nb_users_max)
