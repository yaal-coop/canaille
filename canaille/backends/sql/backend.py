import datetime
from pathlib import Path

from flask import current_app
from flask_alembic import Alembic
from sqlalchemy import create_engine
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import declarative_base
from sqlalchemy_utils import Password

from canaille.backends import Backend
from canaille.backends import ModelEncoder
from canaille.backends import get_lockout_delay_message

Base = declarative_base()


class SQLModelEncoder(ModelEncoder):
    def default(self, obj):
        if isinstance(obj, Password):
            return obj.hash.decode()
        return super().default(obj)


class SQLBackend(Backend):
    engine = None
    db_session = None
    json_encoder = SQLModelEncoder
    alembic = None

    def __init__(self, config):
        super().__init__(config)
        SQLBackend.engine = create_engine(
            self.config["CANAILLE_SQL"]["DATABASE_URI"], echo=False, future=True
        )
        SQLBackend.alembic = Alembic(metadatas=Base.metadata, engines=SQLBackend.engine)

    @classmethod
    def install(cls, app):  # pragma: no cover
        cls.init_alembic(app)
        SQLBackend.alembic.upgrade()

    @classmethod
    def init_alembic(cls, app):
        app.config["ALEMBIC"] = {
            "script_location": str(Path(__file__).resolve().parent / "migrations"),
        }
        SQLBackend.alembic.init_app(app)

    def init_app(self, app, init_backend=None):
        super().init_app(app)
        self.init_alembic(app)
        init_backend = (
            app.config["CANAILLE_SQL"]["AUTO_MIGRATE"]
            if init_backend is None
            else init_backend
        )
        if init_backend:  # pragma: no cover
            with app.app_context():
                self.alembic.upgrade()

    def setup(self):
        if not self.db_session:
            self.db_session = Session(SQLBackend.engine)

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
