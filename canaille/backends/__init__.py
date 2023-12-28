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
        """This methods prepares the database to host canaille data."""
        raise NotImplementedError()

    def setup(self):
        """This method will be called before each http request, it should open
        the connection to the backend."""

    def teardown(self):
        """This method will be called after each http request, it should close
        the connections to the backend."""

    @classmethod
    def validate(cls, config):
        """This method should validate the config part dedicated to the
        backend.

        It should raise :class:`~canaille.configuration.ConfigurationError` when
        errors are met.
        """
        raise NotImplementedError()

    def has_account_lockability(self):
        """Indicates wether the backend supports locking user accounts."""
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
        backend_names = list(app.config.get("BACKENDS", {"memory": {}}).keys())
        backend_name = backend_names[0].lower()
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
