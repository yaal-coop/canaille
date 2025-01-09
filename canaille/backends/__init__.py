import datetime
import importlib
import json
import os
import typing
from contextlib import contextmanager
from math import ceil

from flask import g

from canaille.app import classproperty


class ModelEncoder(json.JSONEncoder):
    """JSON serializer that can handle Canaille models."""

    @staticmethod
    def serialize_model(instance):
        def serialize_attribute(attribute_name, value):
            """Replace model instances by their id."""

            multiple = typing.get_origin(instance.attributes[attribute_name]) is list
            if multiple and isinstance(value, list):
                return [serialize_attribute(attribute_name, v) for v in value]

            model, _ = instance.get_model_annotations(attribute_name)
            if model:
                return value.id

            return value

        result = {}
        for attribute in instance.attributes:
            if serialized := serialize_attribute(
                attribute, getattr(instance, attribute)
            ):
                result[attribute] = serialized

        return result

    def default(self, obj):
        from canaille.backends.models import Model

        if isinstance(obj, datetime.datetime):
            return obj.isoformat()

        if isinstance(obj, Model):
            return self.serialize_model(obj)

        return super().default(obj)


class Backend:
    _instance = None
    json_encoder = ModelEncoder

    def __init__(self, config):
        self.config = config
        Backend._instance = self
        self.register_models()

    @classproperty
    def instance(cls):
        return cls._instance

    def init_app(self, app, init_backend=None):
        @app.before_request
        def before_request():
            return self.setup()

        @app.after_request
        def after_request(response):
            self.teardown()
            return response

    @contextmanager
    def session(self, *args, **kwargs):
        yield self.setup(*args, **kwargs)
        self.teardown()

    @classmethod
    def install(self, app):
        """Prepare the database to host canaille data."""
        raise NotImplementedError()

    def setup(self):
        """Is called before each http request, it should open the connection to
        the backend."""

    def teardown(self):
        """Is called after each http request, it should close the connections
        to the backend."""

    @classmethod
    def validate(cls, config):
        """Validate the config part dedicated to the backend.

        It should raise :class:`~canaille.configuration.ConfigurationError` when
        errors are met.
        """
        raise NotImplementedError()

    def query(self, model, **kwargs):
        """
        Perform a query on the database and return a collection of instances.
        Parameters can be any valid attribute with the expected value:

        >>> backend.query(User, first_name="George")

        If several arguments are passed, the methods only returns the model
        instances that return matches all the argument values:

        >>> backend.query(User, first_name="George", last_name="Abitbol")

        If the argument value is a collection, the methods will return the
        models that matches any of the values:

        >>> backend.query(User, first_name=["George", "Jane"])
        """
        raise NotImplementedError()

    def fuzzy(self, model, query, attributes=None, **kwargs):
        """Works like :meth:`~canaille.backends.Backend.query` but attribute
        values loosely be matched."""
        raise NotImplementedError()

    def get(self, model, identifier=None, **kwargs):
        """Works like :meth:`~canaille.backends.Backend.query` but return only
        one element or :py:data:`None` if no item is matching."""
        raise NotImplementedError()

    def save(self, instance):
        """Validate the current modifications in the database."""
        raise NotImplementedError()

    def delete(self, instance):
        """Remove the current instance from the database."""
        raise NotImplementedError()

    def reload(self, instance):
        """Cancel the unsaved modifications.

        >>> user = User.get(user_name="george")
        >>> user.display_name
        George
        >>> user.display_name = "Jane"
        >>> user.display_name
        Jane
        >>> Backend.instance.reload(user)
        >>> user.display_name
        George
        """
        raise NotImplementedError()

    def update(self, instance, **kwargs):
        """Assign a whole dict to the current instance. This is useful to
        update models based on forms.

        >>> user = User.get(user_name="george")
        >>> user.first_name
        George
        >>> backend.update({
        ...     client,
        ...     first_name="Jane",
        ...     last_name="Calamity",
        ... })
        >>> user.first_name
        Jane
        """
        for attribute, value in kwargs.items():
            setattr(instance, attribute, value)

    def check_user_password(self, user, password: str) -> bool:
        """Check if the password matches the user password in the database."""
        raise NotImplementedError()

    def set_user_password(self, user, password: str):
        """Set a password for the user."""
        raise NotImplementedError()

    def has_account_lockability(self):
        """Indicate whether the backend supports locking user accounts."""
        raise NotImplementedError()

    def register_models(self):
        from canaille.app import models

        module = ".".join(self.__class__.__module__.split(".")[:-1] + ["models"])
        try:
            backend_models = importlib.import_module(module)
        except ModuleNotFoundError:
            return

        model_names = [
            "AuthorizationCode",
            "Client",
            "Consent",
            "Group",
            "Token",
            "User",
        ]
        for model_name in model_names:
            models.register(getattr(backend_models, model_name))


def setup_backend(app, backend=None, init_backend=None):
    if not backend:
        prefix = "CANAILLE_"
        available_backends_names = [
            f"{prefix}{name}".upper() for name in available_backends()
        ]
        configured_backend_names = [
            key[len(prefix) :]
            for key in app.config.keys()
            if key in available_backends_names
        ]
        backend_name = (
            configured_backend_names[0].lower()
            if configured_backend_names
            else "memory"
        )
        module = importlib.import_module(f"canaille.backends.{backend_name}.backend")
        backend_class = getattr(
            module, f"{backend_name.title()}Backend", None
        ) or getattr(module, f"{backend_name.upper()}Backend", None)
        backend = backend_class(app.config)
        backend.init_app(app, init_backend)

    with app.app_context():
        g.backend = backend
        app.backend = backend

    return backend


def available_backends():
    return {
        elt.name
        for elt in os.scandir(os.path.dirname(__file__))
        if elt.is_dir() and os.path.exists(os.path.join(elt, "backend.py"))
    }


def get_lockout_delay_message(current_lockout_delay):
    return f"Too much attempts. Please wait for {ceil(current_lockout_delay)} seconds before trying to login again."
