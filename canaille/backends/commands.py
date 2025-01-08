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

    if typing.get_origin(attribute_type) is typing.Annotated:
        attribute_type = typing.get_args(attribute_type)[0]

    if issubclass(attribute_type, Model):
        return model_getter(attribute_type)

    if attribute_type is datetime.datetime:
        return datetime.datetime.fromisoformat

    return attribute_type


def is_multiple(attribute_type):
    return typing.get_origin(attribute_type) is list


def register(cli):
    """Generate commands using factories that each have one subcommand per
    available model."""
    cli.add_command(get_command)
    cli.add_command(set_command)
    cli.add_command(create_command)
    cli.add_command(delete_command)
    cli.add_command(reset_otp)


def serialize(instance):
    """Quick and dirty serialization method.

    This can probably be made simpler when we will use pydantic models.
    """

    def serialize_attribute(attribute_name, value):
        multiple = is_multiple(instance.attributes[attribute_name])
        if multiple and isinstance(value, list):
            return [serialize_attribute(attribute_name, v) for v in value]

        model, _ = instance.get_model_annotations(attribute_name)
        if model:
            return value.id

        anonymized = ("password",)
        if attribute_name in anonymized and value:
            return "***"

        if isinstance(value, datetime.datetime):
            return value.isoformat()

        return value

    result = {}
    for attribute in instance.attributes:
        if serialized := serialize_attribute(attribute, getattr(instance, attribute)):
            result[attribute] = serialized

    return result


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
        output = json.dumps([serialize(item) for item in items])
        click.echo(output)

    for attribute, attribute_type in model.attributes.items():
        slug = attribute.replace("_", "-")
        click.option(f"--{slug}", type=click_type(attribute_type))(command)

    return command


@click.command(
    cls=ModelCommand, factory=get_factory, name="get", invoke_without_command=True
)
@click.option(
    "--all",
    is_flag=True,
    show_default=True,
    default=False,
    help="Dump all the model instances",
)
@click.pass_context
def get_command(ctx, all: bool):
    """Read information about models.

    Options can be used to filter models::

        canaille get user --given-name John --last-name Doe

    Displays the matching models in JSON format in the standard output.
    """

    if not all and not ctx.invoked_subcommand:
        click.echo(ctx.get_help())
        ctx.exit(0)

    if all:
        objects = {}
        for model_name, model in MODELS.items():
            objects[model_name] = [
                serialize(instance) for instance in Backend.instance.query(model)
            ]

        output = json.dumps(objects)
        click.echo(output)


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

        output = json.dumps(serialize(instance))
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

    The command takes an model ID and edit one or several attributes::

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

        output = json.dumps(serialize(instance))
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


@click.command(cls=ModelCommand, factory=create_factory, name="create")
def create_command():
    """Create models.

    The model attributes can be passed as command options::

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
    @click.argument("identifier")
    def command(*args, identifier, **kwargs):
        instance = Backend.instance.get(model, identifier)
        if not instance:
            raise click.ClickException(
                f"No {model.__name__.lower()} with id '{identifier}'"
            )

        try:
            Backend.instance.delete(instance)
        except Exception as exc:  # pragma: no cover
            raise click.ClickException(exc) from exc

    return command


@click.command(cls=ModelCommand, factory=delete_factory, name="delete")
def delete_command():
    """Delete models.

    The command takes a model ID and deletes it::

        canaille delete user --id 229d112e-1bb5-452f-b2ac-f7680ffe7fb8
    """


@click.command()
@with_appcontext
@with_backendcontext
@click.argument("identifier")
def reset_otp(identifier):
    """Reset one-time password authentication for a user and display the
    edited user in JSON format in the standard output.

    IDENTIFIER should be a user id or user_name
    """

    user = Backend.instance.get(models.User, identifier)
    if not user:
        raise click.ClickException(f"No user with id '{identifier}'")

    user.initialize_otp()
    current_app.logger.security(
        f"Reset one-time password authentication from CLI for {user.user_name}"
    )

    try:
        Backend.instance.save(user)
    except Exception as exc:  # pragma: no cover
        raise click.ClickException(exc) from exc

    output = json.dumps(serialize(user))
    click.echo(output)
