import copy
import datetime
import uuid

import canaille.core.models
import canaille.oidc.models
from canaille.app import models
from canaille.backends.models import Model
from flask import current_app


def listify(value):
    return value if isinstance(value, list) else [value]


def serialize(value):
    return value.id if isinstance(value, MemoryModel) else value


class MemoryModel(Model):
    indexes = {}
    attribute_indexes = {}

    def __init__(self, **kwargs):
        kwargs.setdefault("id", str(uuid.uuid4()))
        self.state = {}
        self.cache = {}
        for attribute, value in kwargs.items():
            setattr(self, attribute, value)

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.id}>"

    @classmethod
    def query(cls, **kwargs):
        # no filter, return all models
        if not kwargs:
            states = cls.index().values()
            return [cls(**state) for state in states]

        # read the attribute indexes
        ids = {
            id
            for attribute, values in kwargs.items()
            for value in listify(values)
            for id in cls.attribute_index(attribute).get(serialize(value), [])
        }
        return [cls(**cls.index()[id]) for id in ids]

    @classmethod
    def index(cls, class_name=None):
        if not class_name:
            class_name = cls.__name__

        return MemoryModel.indexes.setdefault(class_name, {}).setdefault("id", {})

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
                for value in instance.state.get(attribute, [])
                if isinstance(value, str)
            )
        ]

    @classmethod
    def get(cls, identifier=None, **kwargs):
        if identifier:
            kwargs[cls.identifier_attribute] = identifier
        results = cls.query(**kwargs)
        return results[0] if results else None

    def save(self):
        self.delete()

        # update the id index
        self.index()[self.id] = copy.deepcopy(self.state)

        # update the index for each attribute
        for attribute in self.attributes:
            attribute_values = listify(getattr(self, attribute))
            for value in attribute_values:
                self.attribute_index(attribute).setdefault(value, set()).add(self.id)

        # update the mirror attributes of the submodel instances
        for attribute in self.model_attributes:
            klass, mirror_attribute = self.model_attributes[attribute]
            if not self.index(klass) or not mirror_attribute:
                continue

            mirror_attribute_index = self.attribute_index(
                mirror_attribute, klass
            ).setdefault(self.id, set())
            for subinstance_id in self.state.get(attribute, []):
                if not subinstance_id or subinstance_id not in self.index(klass):
                    continue

                subinstance_state = self.index(klass)[subinstance_id]
                subinstance_state.setdefault(mirror_attribute, [])
                subinstance_state[mirror_attribute].append(self.id)

                mirror_attribute_index.add(subinstance_id)

    def delete(self):
        if self.id not in self.index():
            return

        old_state = self.index()[self.id]

        # update the index for each attribute
        for attribute in self.model_attributes:
            attribute_values = listify(old_state.get(attribute, []))
            for value in attribute_values:
                if (
                    value in self.attribute_index(attribute)
                    and self.id in self.attribute_index(attribute)[value]
                ):
                    self.attribute_index(attribute)[value].remove(self.id)

            # update the mirror attributes of the submodel instances
            klass, mirror_attribute = self.model_attributes[attribute]
            if not self.index(klass) or not mirror_attribute:
                continue

            mirror_attribute_index = self.attribute_index(
                mirror_attribute, klass
            ).setdefault(self.id, set())
            for subinstance_id in self.index()[self.id].get(attribute, []):
                if subinstance_id not in self.index(klass):
                    continue

                subinstance_state = self.index(klass)[subinstance_id]
                subinstance_state[mirror_attribute].remove(self.id)

                if subinstance_id in mirror_attribute_index:
                    mirror_attribute_index.remove(subinstance_id)

        # update the index for each attribute
        for attribute in self.attributes:
            attribute_values = listify(old_state.get(attribute, []))
            for value in attribute_values:
                if (
                    value in self.attribute_index(attribute)
                    and self.id in self.attribute_index(attribute)[value]
                ):
                    self.attribute_index(attribute)[value].remove(self.id)

        # update the id index
        del self.index()[self.id]

    def reload(self):
        self.state = self.__class__.get(id=self.id).state
        self.cache = {}

    def __eq__(self, other):
        if other is None:
            return False

        if not isinstance(other, MemoryModel):
            return self == self.__class__.get(id=other)

        return self.state == other.state

    def __hash__(self):
        return hash(self.id)

    def __getattr__(self, name):
        if name in self.attributes:
            values = self.cache.get(name, self.state.get(name, []))

            if name in self.model_attributes:
                klass = getattr(models, self.model_attributes[name][0])
                values = [
                    value if isinstance(value, MemoryModel) else klass.get(id=value)
                    for value in values
                ]
                values = [value for value in values if value]

            unique_attribute = "List" not in str(self.__annotations__[name])
            if unique_attribute:
                return values[0] if values else None
            else:
                return values or []

        raise AttributeError()

    def __setattr__(self, name, value):
        if name in self.attributes:
            values = listify(value)
            self.cache[name] = [value for value in values if value]
            values = [serialize(value) for value in values]
            values = [value for value in values if value]
            self.state[name] = values
        else:
            super().__setattr__(name, value)

    def __html__(self):
        return self.id

    @property
    def identifier(self):
        return getattr(self, self.identifier_attribute)


class User(canaille.core.models.User, MemoryModel):
    identifier_attribute = "user_name"
    model_attributes = {
        "groups": ("Group", "members"),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_permissions()

    def reload(self):
        super().reload()
        self.load_permissions()

    def load_permissions(self):
        self.permissions = set()
        self.read = set()
        self.write = set()
        for access_group_name, details in current_app.config.get("ACL", {}).items():
            if self.match_filter(details.get("FILTER")):
                self.permissions |= set(details.get("PERMISSIONS", []))
                self.read |= set(details.get("READ", []))
                self.write |= set(details.get("WRITE", []))

    def match_filter(self, filter):
        if filter is None:
            return True

        if isinstance(filter, dict):
            # not super generic, but we can improve this when we have
            # type checking and/or pydantic for the models
            if "groups" in filter:
                if models.Group.get(id=filter["groups"]):
                    filter["groups"] = models.Group.get(id=filter["groups"])
                elif models.Group.get(display_name=filter["groups"]):
                    filter["groups"] = models.Group.get(display_name=filter["groups"])

            return all(
                getattr(self, attribute) and value in getattr(self, attribute)
                for attribute, value in filter.items()
            )

        return any(self.match_filter(subfilter) for subfilter in filter)

    @classmethod
    def get_from_login(cls, login=None, **kwargs):
        return User.get(user_name=login)

    def has_password(self):
        return bool(self.password)

    def check_password(self, password):
        if password != self.password:
            return (False, None)

        if self.locked:
            return (False, "Your account has been locked.")

        return (True, None)

    def set_password(self, password):
        self.password = password
        self.save()

    def save(self):
        self.last_modified = datetime.datetime.now(datetime.timezone.utc).replace(
            microsecond=0
        )
        super().save()


class Group(canaille.core.models.Group, MemoryModel):
    model_attributes = {
        "members": ("User", "groups"),
    }
    identifier_attribute = "display_name"


class Client(canaille.oidc.models.Client, MemoryModel):
    identifier_attribute = "client_id"
    model_attributes = {
        "audience": ("Client", None),
    }


class AuthorizationCode(canaille.oidc.models.AuthorizationCode, MemoryModel):
    identifier_attribute = "authorization_code_id"
    model_attributes = {
        "client": ("Client", None),
        "subject": ("User", None),
    }


class Token(canaille.oidc.models.Token, MemoryModel):
    identifier_attribute = "token_id"
    model_attributes = {
        "client": ("Client", None),
        "subject": ("User", None),
        "audience": ("Client", None),
    }


class Consent(canaille.oidc.models.Consent, MemoryModel):
    identifier_attribute = "consent_id"
    model_attributes = {
        "client": ("Client", None),
        "subject": ("User", None),
    }
