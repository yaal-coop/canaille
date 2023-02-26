import functools
import random
import sys

import click
from canaille import create_app
from canaille.i18n import available_language_codes
from canaille.models import Group
from canaille.models import User
from canaille.oidc.models import AuthorizationCode
from canaille.oidc.models import Token
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
    for t in Token.all():
        if t.is_expired():
            t.delete()

    for a in AuthorizationCode.all():
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
        from faker.config import AVAILABLE_LOCALES

        locales = list(set(available_language_codes()) & set(AVAILABLE_LOCALES))
        fake = faker.Faker(locales)
        for i in range(ctx.obj["number"]):
            locale = random.choice(locales)
            profile = fake[locale].profile()
            User(
                cn=profile["name"],
                givenName=profile["name"].split(" ")[0],
                sn=profile["name"].split(" ")[1],
                uid=profile["username"],
                mail=profile["mail"],
                telephoneNumber=profile["ssn"],
                labeledURI=profile["website"][0],
                postalAddress=profile["residence"],
                userPassword=fake.password(),
                locale=locale,
            ).save()

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

        fake = faker.Faker()
        users = User.all()
        for i in range(ctx.obj["number"]):
            group = Group(
                cn=fake.unique.word(),
                description=fake.sentence(),
            )
            nb_users = random.randrange(1, nb_users_max + 1)
            group.member = list({random.choice(users).dn for _ in range(nb_users)})
            group.save()
