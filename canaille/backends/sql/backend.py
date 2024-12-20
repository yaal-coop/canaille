import datetime

from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import declarative_base

from canaille.backends import Backend
from canaille.backends import get_lockout_delay_message

Base = declarative_base()


def db_session(db_uri=None, init=False):
    engine = create_engine(db_uri, echo=False, future=True)
    if init:
        Base.metadata.create_all(engine)
    session = Session(engine)
    return session


class SQLBackend(Backend):
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

        return self.get(User, user_name=login)

    def check_user_password(self, user, password):
        if current_app.features.has_intruder_lockout:
            if current_lockout_delay := user.get_intruder_lockout_delay():
                self.save(user)
                return (False, get_lockout_delay_message(current_lockout_delay))

        if password != user.password:
            if current_app.features.has_intruder_lockout:
                self.record_failed_attempt(user)
            return (False, None)

        if user.locked:
            return (False, "Your account has been locked.")

        return (True, None)

    def set_user_password(self, user, password):
        user.password = password
        user.password_last_update = datetime.datetime.now(
            datetime.timezone.utc
        ).replace(microsecond=0)
        self.save(user)

    def query(self, model, **kwargs):
        filter = [
            model.attribute_filter(attribute_name, expected_value)
            for attribute_name, expected_value in kwargs.items()
        ]
        return (
            SQLBackend.instance.db_session.execute(select(model).filter(*filter))
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

    def get(self, model, identifier=None, /, **kwargs):
        if identifier:
            return (
                self.get(model, **{model.identifier_attribute: identifier})
                or self.get(model, id=identifier)
                or None
            )

        filter = [
            model.attribute_filter(attribute_name, expected_value)
            for attribute_name, expected_value in kwargs.items()
        ]
        return SQLBackend.instance.db_session.execute(
            select(model).filter(*filter)
        ).scalar_one_or_none()

    def save(self, instance):
        # run the instance save callback if existing
        if hasattr(instance, "save"):
            instance.save()

        instance.last_modified = datetime.datetime.now(datetime.timezone.utc).replace(
            microsecond=0
        )
        if not instance.created:
            instance.created = instance.last_modified

        SQLBackend.instance.db_session.add(instance)
        SQLBackend.instance.db_session.commit()

    def delete(self, instance):
        # run the instance delete callback if existing
        save_callback = instance.delete() if hasattr(instance, "delete") else iter([])
        next(save_callback, None)

        SQLBackend.instance.db_session.delete(instance)
        SQLBackend.instance.db_session.commit()

        # run the instance delete callback again if existing
        next(save_callback, None)

    def reload(self, instance):
        # run the instance reload callback if existing
        reload_callback = instance.reload() if hasattr(instance, "reload") else iter([])
        next(reload_callback, None)

        SQLBackend.instance.db_session.refresh(instance)

        # run the instance reload callback again if existing
        next(reload_callback, None)

    def record_failed_attempt(self, user):
        if user.password_failure_timestamps is None:
            user.password_failure_timestamps = []
        user._password_failure_timestamps.append(
            str(datetime.datetime.now(datetime.timezone.utc))
        )
        self.save(user)
