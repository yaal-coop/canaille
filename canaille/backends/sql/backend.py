from sqlalchemy import create_engine
from sqlalchemy import or_
from sqlalchemy import select
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

    def query(self, model, **kwargs):
        filter = [
            model.attribute_filter(attribute_name, expected_value)
            for attribute_name, expected_value in kwargs.items()
        ]
        return (
            Backend.get()
            .db_session.execute(select(model).filter(*filter))
            .scalars()
            .all()
        )

    def fuzzy(self, model, query, attributes=None, **kwargs):
        attributes = attributes or model.attributes
        filter = or_(
            getattr(model, attribute_name).ilike(f"%{query}%")
            for attribute_name in attributes
            if "str" in str(model.attributes[attribute_name])
            # erk, photo is an URL string according to SCIM, but bytes here
            and attribute_name != "photo"
        )

        return self.db_session.execute(select(model).filter(filter)).scalars().all()
