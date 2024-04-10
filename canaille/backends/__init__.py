import importlib
import os
from contextlib import contextmanager

from flask import g


class BaseBackend:
    instance = None

    def __init__(self, config):
        self.config = config
        BaseBackend.instance = self
        self.register_models()

    @classmethod
    def get(cls):
        return cls.instance

    def init_app(self, app):
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
    def install(self, config):
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
        """Works like :meth:`~canaille.backends.BaseBackend.query` but
        attribute values loosely be matched."""
        raise NotImplementedError()

    def check_user_password(self, user, password: str) -> bool:
        """Check if the password matches the user password in the database."""
        raise NotImplementedError()

    def set_user_password(self, user, password: str):
        """Set a password for the user."""
        raise NotImplementedError()

    def has_account_lockability(self):
        """Indicate wether the backend supports locking user accounts."""
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


def setup_backend(app, backend=None):
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
        backend_class = getattr(module, "Backend")
        backend = backend_class(app.config)
        backend.init_app(app)

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
