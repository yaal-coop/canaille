import datetime
import json
import typing

import click
from flask import current_app
from flask.cli import AppGroup
from flask.cli import with_appcontext

from canaille.app import models
from canaille.app.commands import with_backendcontext
from canaille.app.models import MODELS
from canaille.backends import Backend
from canaille.backends.models import Model


class ModelCommand(AppGroup):
    """CLI commands that takes a model subcommand."""

    def __init__(self, *args, factory, **kwargs):
        super().__init__(*args, **kwargs)
        self.factory = factory

    @with_appcontext
    def list_commands(self, ctx):
        base = super().list_commands(ctx)
        lazy = sorted(MODELS.keys())
        return base + lazy

    @with_appcontext
    def get_command(self, ctx, cmd_name):
        model = MODELS.get(cmd_name)
        return self.factory(model)


def model_getter(model):
    """Return a method that gets a model from its id."""
    model_name = model.__name__.lower()
    model = MODELS.get(model_name)

    @with_backendcontext
    def wrapped(id):
        return Backend.instance.get(model, id) if id else None

    return wrapped


def click_type(attribute_type):
    """Find click type for a given model attribute type."""
    if typing.get_origin(attribute_type):
        attribute_type = typing.get_args(attribute_type)[0]

    if typing.get_origin(attribute_type) in (typing.Annotated, list):
        attribute_type = typing.get_args(attribute_type)[0]

    if issubclass(attribute_type, Model):
        return model_getter(attribute_type)

    if attribute_type is datetime.datetime:
        return datetime.datetime.fromisoformat

    return attribute_type


def is_multiple(attribute_type):
    return typing.get_origin(attribute_type) is list


def register(cli):
    """Generate commands using factories that each have one subcommand per available model."""
    cli.add_command(get_command)
    cli.add_command(set_command)
    cli.add_command(create_command)
    cli.add_command(delete_command)
    cli.add_command(reset_otp)
    cli.add_command(dump)
    cli.add_command(restore)


@click.command()
@click.argument("model", required=False, nargs=-1)
@with_appcontext
@with_backendcontext
def dump(model: list[str] | None):
    """Dump all the available models.

    If no argument is passed, all model instances are dumped.
    """
    payload = Backend.instance.dump(model)
    output = json.dumps(payload, cls=Backend.instance.json_encoder)
    click.echo(output)


@click.command()
@click.pass_context
@with_appcontext
@with_backendcontext
def restore(ctx):
    """Restore previously dumped models.

    The dumped models should be passed by the standard input.

    .. code-block:: console

        cat dump.json | canaille restore
    """
    if click.get_text_stream("stdin").isatty() or not (
        stdin := click.get_text_stream("stdin").read().strip()
    ):
        raise click.ClickException("Restore input is missing")

    try:
        payload = json.loads(stdin, object_hook=Backend.instance.json_decode_hook)
    except json.JSONDecodeError as exc:
        message = f"Invalid JSON input.\n{exc}"
        raise click.ClickException(message) from exc

    Backend.instance.restore(payload)


def get_factory(model):
    command_help = f"""Search for {model.__name__.lower()}s and display the
    matching models as JSON."""

    @click.command(name=model.__name__.lower(), help=command_help)
    @with_appcontext
    @with_backendcontext
    def command(*args, **kwargs):
        filter = {
            attribute: value for attribute, value in kwargs.items() if value is not None
        }
        items = Backend.instance.query(model, **filter)
        output = json.dumps(list(items), cls=Backend.instance.json_encoder)
        click.echo(output)

    for attribute, attribute_type in model.attributes.items():
        slug = attribute.replace("_", "-")
        click.option(
            f"--{slug}",
            type=click_type(attribute_type),
        )(command)

    return command


@click.command(cls=ModelCommand, factory=get_factory, name="get")
def get_command():
    """Read information about models.

    Options can be used to filter models:

    .. code-block:: console

        canaille get user --given-name John --last-name Doe

    Displays the matching models in JSON format in the standard output.
    """


def set_factory(model):
    command_help = f"""Update a {model.__name__.lower()} and display the
    edited model in JSON format in the standard output.

    IDENTIFIER should be a {model.__name__.lower()} id or
    {model.identifier_attribute}
    """

    @click.command(name=model.__name__.lower(), help=command_help)
    @with_appcontext
    @with_backendcontext
    @click.argument("identifier")
    def command(*args, identifier, **kwargs):
        instance = Backend.instance.get(model, identifier)
        if not instance:
            raise click.ClickException(
                f"No {model.__name__.lower()} with id '{identifier}'"
            )

        for attribute, value in kwargs.items():
            multiple = is_multiple(model.attributes[attribute])
            if multiple:
                if value != ():
                    value = [v for v in value if v]
                    setattr(instance, attribute, value)

            elif value is not None:
                setattr(instance, attribute, value or None)

        try:
            Backend.instance.save(instance)
        except Exception as exc:  # pragma: no cover
            raise click.ClickException(exc) from exc

        output = json.dumps(instance, cls=Backend.instance.json_encoder)
        click.echo(output)

    attributes = dict(model.attributes)
    del attributes["id"]
    for attribute, attribute_type in attributes.items():
        slug = attribute.replace("_", "-")
        click.option(
            f"--{slug}",
            type=click_type(attribute_type),
            multiple=is_multiple(attribute_type),
        )(command)

    return command


@click.command(cls=ModelCommand, factory=set_factory, name="set")
def set_command():
    """Update models.

    The command takes an model ID and edit one or several attributes:

    .. code-block:: console

        canaille set user 229d112e-1bb5-452f-b2ac-f7680ffe7fb8 --given-name Jack

    Displays the edited model in JSON format in the standard output.
    """


def create_factory(model):
    command_help = f"""Create a new {model.__name__.lower()} and display the
    created model in JSON format in the standard output.
    """

    @click.command(name=model.__name__.lower(), help=command_help)
    @with_appcontext
    @with_backendcontext
    def command(*args, **kwargs):
        attributes = {}
        for attribute, value in kwargs.items():
            multiple = is_multiple(model.attributes[attribute])
            if multiple:
                value = list(value)

            if value is not None and value != []:
                attributes[attribute] = value

        instance = model(**attributes)

        try:
            Backend.instance.save(instance)
        except Exception as exc:  # pragma: no cover
            raise click.ClickException(exc) from exc

        output = json.dumps(instance, cls=Backend.instance.json_encoder)
        click.echo(output)

    basemodel = [klass for klass in model.__bases__ if issubclass(klass, Model)][0]
    attributes = dict(basemodel.attributes)
    del attributes["id"]
    for attribute, attribute_type in attributes.items():
        slug = attribute.replace("_", "-")
        click.option(
            f"--{slug}",
            type=click_type(attribute_type),
            multiple=is_multiple(attribute_type),
        )(command)

    return command


@click.command(cls=ModelCommand, factory=create_factory, name="create")
def create_command():
    """Create models.

    The model attributes can be passed as command options:

    .. code-block:: console

        canaille create user --given-name John --last-name Doe

    Displays the created model in JSON format in the standard output.
    """


def delete_factory(model):
    command_help = f"""Delete a {model.__name__.lower()}.

    IDENTIFIER should be a {model.__name__.lower()} id or
    {model.identifier_attribute}
    """

    @click.command(name=model.__name__.lower(), help=command_help)
    @with_appcontext
    @with_backendcontext
    @click.option(
        "--noconfirm",
        is_flag=True,
        default=False,
        help="Ask for confirmation before deleting objects.",
    )
    def command(*args, noconfirm, **kwargs):
        filter = {
            attribute: value for attribute, value in kwargs.items() if value is not None
        }
        items = Backend.instance.query(model, **filter)

        if len(items) > 0 and not noconfirm:
            confirmation = click.confirm(
                f"{len(items)} will be deleted. Do you confirm?"
            )
            if not confirmation:
                return

        for obj in items:
            try:
                Backend.instance.delete(obj)
            except Exception as exc:  # pragma: no cover
                raise click.ClickException(exc) from exc

        click.echo(f"{len(items)} item(s) deleted.")

    for attribute, attribute_type in model.attributes.items():
        slug = attribute.replace("_", "-")
        click.option(
            f"--{slug}",
            type=click_type(attribute_type),
        )(command)

    return command


@click.command(cls=ModelCommand, factory=delete_factory, name="delete")
def delete_command():
    """Delete models.

    The command takes a model ID and deletes it.
    By default all models are deleted, to restrict the deletion parameters like ``--id`` can be used,
    then only the items matching the filters will be deleted:

    .. code-block:: console

        canaille delete user --id 229d112e-1bb5-452f-b2ac-f7680ffe7fb8
    """


@click.command()
@with_appcontext
@with_backendcontext
@click.argument("identifier")
def reset_otp(identifier):
    """Reset one-time password authentication for a user and display the edited user in JSON format in the standard output.

    IDENTIFIER should be a user id or user_name
    """
    from canaille.app.otp import initialize_otp

    user = Backend.instance.get(models.User, identifier)
    if not user:
        raise click.ClickException(f"No user with id '{identifier}'")

    initialize_otp(user)
    current_app.logger.security(
        f"Reset one-time password authentication from CLI for {user.user_name}"
    )

    try:
        Backend.instance.save(user)
    except Exception as exc:  # pragma: no cover
        raise click.ClickException(exc) from exc

    output = json.dumps(user, cls=Backend.instance.json_encoder)
    click.echo(output)
