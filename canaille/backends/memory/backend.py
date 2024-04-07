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

    def get_user_from_login(self, login):
        from .models import User

        return User.get(user_name=login)

    def check_user_password(self, user, password):
        if password != user.password:
            return (False, None)

        if user.locked:
            return (False, "Your account has been locked.")

        return (True, None)

    def set_user_password(self, user, password):
        user.password = password
        user.save()
