class Backend:
    def __init__(self, app):
        self.app = app

        @self.app.before_request
        def before_request():
            if not app.config["TESTING"]:
                return self.setup()

        @self.app.after_request
        def after_request(response):
            if not app.config["TESTING"]:
                self.teardown()
            return response

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
