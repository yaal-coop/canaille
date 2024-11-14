import json

import click
from flask.cli import with_appcontext

from canaille.app import models
from canaille.app.commands import with_backendcontext
from canaille.backends import Backend
from canaille.backends.commands import serialize

try:
    HAS_FAKER = True
except ImportError:
    HAS_FAKER = False


@click.group()
@click.option("--nb", default=1, help="Number of items to create")
@click.pass_context
@with_appcontext
def populate(ctx, nb):
    """Populate the database with generated random data."""
    ctx.ensure_object(dict)

    ctx.obj["number"] = nb


@populate.command()
@click.pass_context
@with_appcontext
@with_backendcontext
def users(ctx):
    """Populate the database with generated random users."""
    from canaille.core.populate import fake_users

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
    """Populate the database with generated random groups."""
    from canaille.core.populate import fake_groups

    fake_groups(ctx.obj["number"], nb_users_max)


def register(cli):
    if HAS_FAKER:  # pragma: no branch
        cli.add_command(populate)
    cli.add_command(reset_mfa)


@click.command()
@with_appcontext
@with_backendcontext
@click.argument("identifier")
def reset_mfa(identifier):
    """Reset multi-factor authentication for a user and display the
    edited user in JSON format in the standard output.

    IDENTIFIER should be a user id or user_name
    """

    instance = Backend.instance.get(models.User, identifier)
    if not instance:
        raise click.ClickException(f"No user with id '{identifier}'")

    instance.initialize_otp()

    try:
        Backend.instance.save(instance)
    except Exception as exc:  # pragma: no cover
        raise click.ClickException(exc) from exc

    output = json.dumps(serialize(instance))
    click.echo(output)
