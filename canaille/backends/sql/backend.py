from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import declarative_base

from canaille.backends import BaseBackend

Base = declarative_base()


def db_session(db_uri=None, init=False):
    engine = create_engine(db_uri, echo=False, future=True)
    if init:
        Base.metadata.create_all(engine)
    session = Session(engine)
    return session


class Backend(BaseBackend):
    db_session = None

    @classmethod
    def install(cls, config):  # pragma: no cover
        engine = create_engine(
            config["CANAILLE_SQL"]["DATABASE_URI"],
            echo=False,
            future=True,
        )
        Base.metadata.create_all(engine)

    def setup(self, init=False):
        if not self.db_session:
            self.db_session = db_session(
                self.config["CANAILLE_SQL"]["DATABASE_URI"],
                init=init,
            )

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
