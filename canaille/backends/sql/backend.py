import datetime
import inspect
from pathlib import Path

from flask import current_app
from flask_alembic import Alembic
from sqlalchemy import create_engine
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm import declarative_base
from sqlalchemy_utils import Password

from canaille.app.configuration import CheckResult
from canaille.app.models import MODELS
from canaille.backends import Backend
from canaille.backends import ModelEncoder
from canaille.backends import get_lockout_delay_message
from canaille.backends.models import Model

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
        SQLBackend.alembic = Alembic(
            metadatas=Base.metadata, engines=SQLBackend.engine, run_mkdir=False
        )

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
    def check_network_config(cls, config):
        sess = Session(SQLBackend.engine)
        sess.execute(text("SELECT 1"))
        return CheckResult(success=True, message="SQL database correctly configured")

    def has_account_lockability(self):
        return True

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

    def do_query(self, model, *args, **kwargs):
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

    def do_restore(self, payload):
        # Create models without references to other models
        # We *could* do this in one single loop, but Client.audience is self-referencing,
        # so it has to be created first, and then must be added to its own audience.
        for model_name, model in MODELS.items():
            states = payload.get(model_name, [])
            for state in states:
                sql_state = self.filter_state(
                    model, state, keep_non_model_and_required_attrs=True
                )
                sql_state = self.replace_ids_with_instances(model, sql_state)
                obj = model(**sql_state)
                Backend.instance.save(obj)

        # Insert model references
        for model_name, model in MODELS.items():
            states = payload.get(model_name, [])
            for state in states:
                obj_id = state["id"]
                sql_state = self.filter_state(
                    model, state, keep_non_model_and_required_attrs=False
                )
                sql_state = self.replace_ids_with_instances(model, sql_state)
                obj = Backend.instance.get(model, obj_id)
                for attr, value in sql_state.items():
                    setattr(obj, attr, value)
                Backend.instance.save(obj)

    @classmethod
    def filter_state(cls, model, state, keep_non_model_and_required_attrs):
        def filter_attribute(attr):
            type_, _ = model.get_model_annotations(attr)
            is_non_model = not inspect.isclass(type_) or not issubclass(type_, Model)
            is_required = model.is_attr_required(attr)
            is_writable = not model.is_attr_readonly(attr)
            valid = (
                is_writable
                and (is_non_model or is_required) == keep_non_model_and_required_attrs
            )
            return valid

        return {attr: value for attr, value in state.items() if filter_attribute(attr)}

    @classmethod
    def replace_ids_with_instances(cls, model, state):
        for attr, value in state.items():
            generic_attr_model, _ = model.get_model_annotations(attr)
            if not generic_attr_model:
                continue

            model_name = generic_attr_model.__name__.lower()
            backend_attr_model = MODELS.get(model_name)
            if isinstance(value, list):
                state[attr] = [
                    Backend.instance.get(backend_attr_model, id_) for id_ in value
                ]
            else:
                state[attr] = Backend.instance.get(backend_attr_model, value)

        return state

    def do_save(self, instance):
        instance.last_modified = datetime.datetime.now(datetime.timezone.utc).replace(
            microsecond=0
        )
        if not instance.created:
            instance.created = instance.last_modified

        SQLBackend.instance.db_session.add(instance)
        SQLBackend.instance.db_session.commit()

    def do_delete(self, instance):
        SQLBackend.instance.db_session.delete(instance)
        SQLBackend.instance.db_session.commit()

    def do_reload(self, instance):
        SQLBackend.instance.db_session.refresh(instance)

    def record_failed_attempt(self, user):
        if user.password_failure_timestamps is None:
            user.password_failure_timestamps = []
        user._password_failure_timestamps.append(
            str(datetime.datetime.now(datetime.timezone.utc))
        )
        self.save(user)
