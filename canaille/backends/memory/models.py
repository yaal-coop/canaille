import copy
import datetime
import typing
import uuid
from typing import ClassVar
from typing import Dict
from typing import Optional

import canaille.core.models
import canaille.oidc.models
from canaille.app import models
from canaille.backends.models import BackendModel


class MemoryModel(BackendModel):
    indexes = {}
    """Associates ids and states."""

    attribute_indexes = {}
    """Associates attribute values and ids."""

    def __init__(self, *args, **kwargs):
        self._state = {}
        self._cache = {}
        for attribute, value in kwargs.items():
            setattr(self, attribute, value)

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id}>"

    @classmethod
    def query(cls, **kwargs):
        # if there is no filter, return all models
        if not kwargs:
            states = cls.index().values()
            return [cls(**state) for state in states]

        # get the ids from the attribute indexes
        ids = {
            id
            for attribute, values in kwargs.items()
            for value in cls.serialize(cls.listify(values))
            for id in cls.attribute_index(attribute).get(value, [])
        }

        # get the states from the ids
        states = [cls.index()[id] for id in ids]

        # initialize instances from the states
        return [cls(**state) for state in states]

    @classmethod
    def index(cls, class_name=None):
        return MemoryModel.indexes.setdefault(class_name or cls.__name__, {})

    @classmethod
    def attribute_index(cls, attribute="id", class_name=None):
        return MemoryModel.attribute_indexes.setdefault(
            class_name or cls.__name__, {}
        ).setdefault(attribute, {})

    @classmethod
    def fuzzy(cls, query, attributes=None, **kwargs):
        attributes = attributes or cls.attributes
        instances = cls.query(**kwargs)

        return [
            instance
            for instance in instances
            if any(
                query.lower() in value.lower()
                for attribute in attributes
                for value in cls.listify(instance._state.get(attribute, []))
                if isinstance(value, str)
            )
        ]

    @classmethod
    def get(cls, identifier=None, /, **kwargs):
        if identifier:
            return (
                cls.get(**{cls.identifier_attribute: identifier})
                or cls.get(id=identifier)
                or None
            )

        results = cls.query(**kwargs)
        return results[0] if results else None

    @classmethod
    def listify(cls, value):
        return value if isinstance(value, list) else [value]

    @classmethod
    def serialize(cls, value):
        if isinstance(value, list):
            values = [cls.serialize(item) for item in value]
            return [item for item in values if item]

        return value.id if isinstance(value, MemoryModel) else value

    @classmethod
    def deserialize(cls, attribute_name, value):
        if isinstance(value, list):
            values = [cls.deserialize(attribute_name, item) for item in value]
            return [item for item in values if item]

        if not value:
            multiple_attribute = (
                typing.get_origin(cls.attributes[attribute_name]) is list
            )
            return [] if multiple_attribute else None

        if attribute_name in cls.model_attributes and not isinstance(
            value, MemoryModel
        ):
            model = getattr(models, cls.model_attributes[attribute_name][0])
            return model.get(id=value)

        return value

    def save(self):
        if not self.id:
            self.id = str(uuid.uuid4())

        self.last_modified = datetime.datetime.now(datetime.timezone.utc).replace(
            microsecond=0
        )
        if not self.created:
            self.created = self.last_modified

        self.index_delete()
        self.index_save()

    def delete(self):
        self.index_delete()

    def index_save(self):
        # update the id index
        self.index()[self.id] = copy.deepcopy(self._state)

        # update the index for each attribute
        for attribute in self.attributes:
            attribute_values = self.listify(self._state.get(attribute, []))
            for value in attribute_values:
                self.attribute_index(attribute).setdefault(value, set()).add(self.id)

        # update the mirror attributes of the submodel instances
        for attribute in self.model_attributes:
            model, mirror_attribute = self.model_attributes[attribute]
            if not self.index(model) or not mirror_attribute:
                continue

            mirror_attribute_index = self.attribute_index(
                mirror_attribute, model
            ).setdefault(self.id, set())
            for subinstance_id in self.listify(self._state.get(attribute, [])):
                # add the current objet in the subinstance state
                subinstance_state = self.index(model)[subinstance_id]
                subinstance_state.setdefault(mirror_attribute, [])
                subinstance_state[mirror_attribute].append(self.id)

                # add the current objet in the subinstance index
                mirror_attribute_index.add(subinstance_id)

    def index_delete(self):
        if self.id not in self.index():
            return

        old_state = self.index()[self.id]

        # update the mirror attributes of the submodel instances
        for attribute in self.model_attributes:
            attribute_values = self.listify(old_state.get(attribute, []))
            for value in attribute_values:
                self.attribute_index(attribute)[value].remove(self.id)

            # update the mirror attributes of the submodel instances
            model, mirror_attribute = self.model_attributes[attribute]
            if not self.index(model) or not mirror_attribute:
                continue

            mirror_attribute_index = self.attribute_index(
                mirror_attribute, model
            ).setdefault(self.id, set())
            for subinstance_id in self.index()[self.id].get(attribute, []):
                # remove the current objet from the subinstance state
                subinstance_state = self.index(model)[subinstance_id]
                subinstance_state[mirror_attribute].remove(self.id)

                # remove the current objet from the subinstance index
                mirror_attribute_index.remove(subinstance_id)

        # update the index for each attribute
        for attribute in self.attributes:
            attribute_values = self.listify(old_state.get(attribute, []))
            for value in attribute_values:
                if (
                    value in self.attribute_index(attribute)
                    and self.id in self.attribute_index(attribute)[value]
                ):
                    self.attribute_index(attribute)[value].remove(self.id)

        # update the id index
        del self.index()[self.id]

    def reload(self):
        self._state = self.__class__.get(id=self.id)._state
        self._cache = {}

    def __eq__(self, other):
        if other is None:
            return False

        if not isinstance(other, MemoryModel):
            return self == self.__class__.get(id=other)

        return self._state == other._state

    def __hash__(self):
        return hash(self.id)

    def __getattribute__(self, name):
        if name != "attributes" and name in self.attributes:
            return self.deserialize(name, self._cache.get(name, self._state.get(name)))

        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name in self.attributes:
            self._cache[name] = value
            self._state[name] = self.serialize(value)
        else:
            super().__setattr__(name, value)

    @property
    def identifier(self):
        return getattr(self, self.identifier_attribute)


class User(canaille.core.models.User, MemoryModel):
    identifier_attribute: ClassVar[str] = "user_name"
    model_attributes: ClassVar[Dict[str, Optional[str]]] = {
        "groups": ("Group", "members"),
    }


class Group(canaille.core.models.Group, MemoryModel):
    identifier_attribute: ClassVar[str] = "display_name"
    model_attributes: ClassVar[Dict[str, Optional[str]]] = {
        "members": ("User", "groups"),
    }


class Client(canaille.oidc.models.Client, MemoryModel):
    identifier_attribute: ClassVar[str] = "client_id"
    model_attributes: ClassVar[Dict[str, Optional[str]]] = {
        "audience": ("Client", None),
    }


class AuthorizationCode(canaille.oidc.models.AuthorizationCode, MemoryModel):
    identifier_attribute: ClassVar[str] = "authorization_code_id"
    model_attributes: ClassVar[Dict[str, Optional[str]]] = {
        "client": ("Client", None),
        "subject": ("User", None),
    }


class Token(canaille.oidc.models.Token, MemoryModel):
    identifier_attribute: ClassVar[str] = "token_id"
    model_attributes: ClassVar[Dict[str, Optional[str]]] = {
        "client": ("Client", None),
        "subject": ("User", None),
        "audience": ("Client", None),
    }


class Consent(canaille.oidc.models.Consent, MemoryModel):
    identifier_attribute: ClassVar[str] = "consent_id"
    model_attributes: ClassVar[Dict[str, Optional[str]]] = {
        "client": ("Client", None),
        "subject": ("User", None),
    }
