from contextlib import contextmanager


class Backend:
    instance = None

    def __init__(self, config):
        Backend.instance = self

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
    def session(self):
        yield self.setup()
        self.teardown()

    @classmethod
    def install(self):
        """
        This methods prepares the database to host canaille data.
        """
        raise NotImplementedError()

    def setup(self):
        """
        This method will be called before each http request,
        it should open the connection to the backend.
        """
        raise NotImplementedError()

    def teardown(self):
        """
        This method will be called after each http request,
        it should close the connections to the backend.
        """
        raise NotImplementedError()

    @classmethod
    def validate(cls, config):
        """
        This method should validate the config part dedicated to the backend.
        It should raise :class:`~canaille.configuration.ConfigurationError` when
        errors are met.
        """
        raise NotImplementedError()

    def has_account_lockability(self):
        """
        Indicates wether the backend supports locking user accounts.
        """
        raise NotImplementedError()
