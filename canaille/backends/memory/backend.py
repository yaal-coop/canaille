from canaille.backends import BaseBackend


class Backend(BaseBackend):
    @classmethod
    def install(cls, config):
        pass

    def setup(self):
        pass

    def teardown(self):
        pass

    @classmethod
    def validate(cls, config):
        pass

    @classmethod
    def login_placeholder(cls):
        return ""

    def has_account_lockability(self):
        return True
