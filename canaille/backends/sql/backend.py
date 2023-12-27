from canaille.backends import BaseBackend
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session


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
            config["BACKENDS"]["SQL"]["SQL_DATABASE_URI"],
            echo=False,
            future=True,
        )
        Base.metadata.create_all(engine)

    def setup(self, init=False):
        if not self.db_session:
            self.db_session = db_session(
                self.config["BACKENDS"]["SQL"]["SQL_DATABASE_URI"],
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
