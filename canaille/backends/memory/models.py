import typing

import canaille.core.models
import canaille.oidc.models
from canaille.app import models
from canaille.backends import Backend
from canaille.backends.models import BackendModel


class MemoryModel(BackendModel):
    def __init__(self, *args, **kwargs):
        self._state = {}
        self._cache = {}
        for attribute, value in kwargs.items():
            setattr(self, attribute, value)

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id}>"

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

        model, _ = cls.get_model_annotations(attribute_name)
        if model and not isinstance(value, model):
            backend_model = getattr(models, model.__name__)
            return Backend.instance.get(backend_model, id=value)

        return value

    def __eq__(self, other):
        if other is None:
            return False

        if not isinstance(other, MemoryModel):
            return self == Backend.instance.get(self.__class__, id=other)

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


class User(canaille.core.models.User, MemoryModel):
    pass


class Group(canaille.core.models.Group, MemoryModel):
    pass


class Client(canaille.oidc.models.Client, MemoryModel):
    pass


class AuthorizationCode(canaille.oidc.models.AuthorizationCode, MemoryModel):
    pass


class Token(canaille.oidc.models.Token, MemoryModel):
    pass


class Consent(canaille.oidc.models.Consent, MemoryModel):
    pass
