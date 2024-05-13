import datetime
import inspect
import json
import typing

import click
from flask.cli import AppGroup
from flask.cli import with_appcontext

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
    factories = [get_factory, set_factory, create_factory, delete_factory]

    for factory in factories:
        command_help = inspect.getdoc(factory)
        name = factory.__name__.replace("_factory", "")

        @cli.command(cls=ModelCommand, factory=factory, name=name, help=command_help)
        def factory_command(): ...


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
    """Read informations about models.

    Options can be used to filter models::

        canaille get user --given-name John --last-name Doe

    Displays the matching models in JSON format in the standard output.
    """

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


def set_factory(model):
    """Update models.

    The command takes an model ID and edit one or several attributes::

        canaille set user 229d112e-1bb5-452f-b2ac-f7680ffe7fb8 --given-name Jack

    Displays the edited model in JSON format in the standard output.
    """

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


def create_factory(model):
    """Create models.

    The model attributes can be passed as command options::

        canaille create user --given-name John --last-name Doe

    Displays the created model in JSON format in the standard output.
    """

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


def delete_factory(model):
    """Delete models.

    The command takes a model ID and deletes it::

        canaille delete user --id 229d112e-1bb5-452f-b2ac-f7680ffe7fb8
    """

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
