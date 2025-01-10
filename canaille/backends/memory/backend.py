import copy
import datetime
import uuid
from typing import Any

from flask import current_app

import canaille.backends.memory.models
from canaille.backends import Backend
from canaille.backends import get_lockout_delay_message


def listify(value):
    if value is None:
        return []

    return value if isinstance(value, list) else [value]


class MemoryBackend(Backend):
    indexes: dict[str, dict[str, Any]] = None
    """Associates ids and states."""

    attribute_indexes = None
    """Associates attribute values and ids."""

    def index(self, model):
        if not self.indexes:
            self.indexes = {}

        model_name = model if isinstance(model, str) else model.__name__
        return self.indexes.setdefault(model_name, {})

    def attribute_index(self, model, attribute="id"):
        if not self.attribute_indexes:
            self.attribute_indexes = {}

        model_name = model if isinstance(model, str) else model.__name__
        return self.attribute_indexes.setdefault(model_name, {}).setdefault(
            attribute, {}
        )

    @classmethod
    def install(cls, app):
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
        # if there is no filter, return all models
        if not kwargs:
            states = self.index(model).values()
            return [model(**state) for state in states]

        # get the ids from the attribute indexes
        ids = {
            id
            for attribute, values in kwargs.items()
            for value in model.serialize(listify(values))
            for id in self.attribute_index(model, attribute).get(value, [])
        }

        # get the states from the ids
        states = [self.index(model)[id] for id in ids]

        # initialize instances from the states
        instances = [model(**state) for state in states]
        for instance in instances:
            # TODO: maybe find a way to not initialize the cache in the first place?
            instance._cache = {}

        return instances

    def fuzzy(self, model, query, attributes=None, **kwargs):
        attributes = attributes or model.attributes
        instances = self.query(model, **kwargs)

        return [
            instance
            for instance in instances
            if any(
                query.lower() in value.lower()
                for attribute in attributes
                for value in listify(instance._state.get(attribute, []))
                if isinstance(value, str)
            )
        ]

    def get(self, model, identifier=None, /, **kwargs):
        if identifier:
            return (
                self.get(model, **{model.identifier_attribute: identifier})
                or self.get(model, id=identifier)
                or None
            )

        results = self.query(model, **kwargs)
        return results[0] if results else None

    def save(self, instance):
        if (
            isinstance(instance, canaille.backends.memory.models.User)
            and current_app.features.has_otp
            and not instance.secret_token
        ):
            instance.initialize_otp()

        if not instance.id:
            instance.id = str(uuid.uuid4())

        instance.last_modified = datetime.datetime.now(datetime.timezone.utc).replace(
            microsecond=0
        )
        if not instance.created:
            instance.created = instance.last_modified

        self.index_delete(instance)
        self.index_save(instance)
        instance._cache = {}

    def delete(self, instance):
        # run the instance delete callback if existing
        delete_callback = instance.delete() if hasattr(instance, "delete") else iter([])
        next(delete_callback, None)

        self.index_delete(instance)

        # run the instance delete callback again if existing
        next(delete_callback, None)

    def reload(self, instance):
        # run the instance reload callback if existing
        reload_callback = instance.reload() if hasattr(instance, "reload") else iter([])
        next(reload_callback, None)

        instance._state = Backend.instance.get(
            instance.__class__, id=instance.id
        )._state
        instance._cache = {}

        # run the instance reload callback again if existing
        next(reload_callback, None)

    def index_save(self, instance):
        # update the id index
        self.index(instance.__class__)[instance.id] = copy.deepcopy(instance._state)

        # update the index for each attribute
        for attribute in instance.attributes:
            attribute_values = listify(instance._state.get(attribute, []))
            for value in attribute_values:
                self.attribute_index(instance.__class__, attribute).setdefault(
                    value, set()
                ).add(instance.id)

        # update the mirror attributes of the submodel instances
        for attribute in instance.attributes:
            model, mirror_attribute = instance.get_model_annotations(attribute)
            if not model or not self.index(model) or not mirror_attribute:
                continue

            mirror_attribute_index = self.attribute_index(
                model, mirror_attribute
            ).setdefault(instance.id, set())
            for subinstance_id in listify(instance._state.get(attribute, [])):
                # add the current object in the subinstance state
                subinstance_state = self.index(model)[subinstance_id]
                subinstance_state.setdefault(mirror_attribute, [])
                subinstance_state[mirror_attribute].append(instance.id)

                # add the current object in the subinstance index
                mirror_attribute_index.add(subinstance_id)

    def index_delete(self, instance):
        if instance.id not in self.index(instance.__class__):
            return

        old_state = self.index(instance.__class__)[instance.id]

        # update the index for each attribute
        for attribute in instance.attributes:
            attribute_values = listify(old_state.get(attribute, []))
            for value in attribute_values:
                self.attribute_index(instance.__class__, attribute)[value].remove(
                    instance.id
                )

            # update the mirror attributes of the submodel instances
            model, mirror_attribute = instance.get_model_annotations(attribute)
            if not model or not self.index(model) or not mirror_attribute:
                continue

            mirror_attribute_index = self.attribute_index(
                model, mirror_attribute
            ).setdefault(instance.id, set())
            for subinstance_id in self.index(instance.__class__)[instance.id].get(
                attribute, []
            ):
                # remove the current object from the subinstance state
                subinstance_state = self.index(model)[subinstance_id]
                subinstance_state[mirror_attribute].remove(instance.id)

                # remove the current object from the subinstance index
                mirror_attribute_index.remove(subinstance_id)

        # update the id index
        del self.index(instance.__class__)[instance.id]

    def record_failed_attempt(self, user):
        user.password_failure_timestamps += [
            datetime.datetime.now(datetime.timezone.utc)
        ]
        self.save(user)
