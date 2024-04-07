import datetime
import inspect
import typing
from collections import ChainMap
from typing import Optional

from canaille.app import classproperty
from canaille.app import models


class Model:
    """The model abstract class.

    It details all the common attributes shared by every models.
    """

    id: Optional[str] = None
    """A unique identifier for a SCIM resource as defined by the service
    provider. Id will be :py:data:`None` until the
    :meth:`~canaille.backends.models.BackendModel.save` method is called.

    Each representation of the resource MUST include a non-empty "id"
    value.  This identifier MUST be unique across the SCIM service
    provider's entire set of resources.  It MUST be a stable, non-
    reassignable identifier that does not change when the same resource
    is returned in subsequent requests.  The value of the "id" attribute
    is always issued by the service provider and MUST NOT be specified
    by the client.  The string "bulkId" is a reserved keyword and MUST
    NOT be used within any unique identifier value.  The attribute
    characteristics are "caseExact" as "true", a mutability of
    "readOnly", and a "returned" characteristic of "always".  See
    Section 9 for additional considerations regarding privacy.
    """

    created: Optional[datetime.datetime] = None
    """The :class:`~datetime.datetime` that the resource was added to the
    service provider."""

    last_modified: Optional[datetime.datetime] = None
    """The most recent :class:`~datetime.datetime` that the details of this
    resource were updated at the service provider.

    If this resource has never been modified since its initial creation,
    the value MUST be the same as the value of :attr:`~canaille.backends.models.Model.created`.
    """

    _attributes = None

    @classproperty
    def attributes(cls):
        if not cls._attributes:
            annotations = ChainMap(
                *(
                    typing.get_type_hints(klass)
                    for klass in reversed(cls.__mro__)
                    if issubclass(klass, Model)
                )
            )
            # only keep types that are not typing.ClassVar
            cls._attributes = {
                key: value
                for key, value in annotations.items()
                if typing.get_origin(value) is not typing.ClassVar
            }
        return cls._attributes


class BackendModel:
    """The backend model abstract class.

    It details all the methods and attributes that are expected to be
    implemented for every model and for every backend.
    """

    @classmethod
    def query(cls, **kwargs):
        """
        Performs a query on the database and return a collection of instances.
        Parameters can be any valid attribute with the expected value:

        >>> User.query(first_name="George")

        If several arguments are passed, the methods only returns the model
        instances that return matches all the argument values:

        >>> User.query(first_name="George", last_name="Abitbol")

        If the argument value is a collection, the methods will return the
        models that matches any of the values:

        >>> User.query(first_name=["George", "Jane"])
        """
        raise NotImplementedError()

    @classmethod
    def fuzzy(cls, query, attributes=None, **kwargs):
        """Works like :meth:`~canaille.backends.models.BackendModel.query` but
        attribute values loosely be matched."""
        raise NotImplementedError()

    @classmethod
    def get(cls, identifier=None, **kwargs):
        """Works like :meth:`~canaille.backends.models.BackendModel.query` but
        return only one element or :py:data:`None` if no item is matching."""
        raise NotImplementedError()

    @property
    def identifier(self):
        """Returns a unique value that will be used to identify the model
        instance.

        This value will be used in URLs in canaille, so it should be
        unique and short.
        """
        raise NotImplementedError()

    def save(self):
        """Validates the current modifications in the database."""
        raise NotImplementedError()

    def delete(self):
        """Removes the current instance from the database."""
        raise NotImplementedError()

    def update(self, **kwargs):
        """Assign a whole dict to the current instance. This is useful to
        update models based on forms.

        >>> user = User.get(user_name="george")
        >>> user.first_name
        George
        >>> user.update({
        ...     first_name="Jane",
        ...     last_name="Calamity",
        ... })
        >>> user.first_name
        Jane
        """
        for attribute, value in kwargs.items():
            setattr(self, attribute, value)

    def reload(self):
        """Cancels the unsaved modifications.

        >>> user = User.get(user_name="george")
        >>> user.display_name
        George
        >>> user.display_name = "Jane"
        >>> user.display_name
        Jane
        >>> user.reload()
        >>> user.display_name
        George
        """
        raise NotImplementedError()

    @classmethod
    def get_attribute_type(cls, attribute_name):
        """Reads the attribute typing and extract the type, possibly burried
        under list or Optional."""
        attribute = cls.attributes[attribute_name]
        core_type = (
            typing.get_args(attribute)[0]
            if typing.get_origin(attribute) == list
            else attribute
        )
        return (
            typing._eval_type(core_type, globals(), locals())
            if isinstance(core_type, typing.ForwardRef)
            else core_type
        )

    def match_filter(self, filter):
        if filter is None:
            return True

        if isinstance(filter, list):
            return any(self.match_filter(subfilter) for subfilter in filter)

        # If attribute are models, resolve the instance
        for attribute, value in filter.items():
            attribute_type = self.get_attribute_type(attribute)

            if not inspect.isclass(attribute_type) or not issubclass(
                attribute_type, Model
            ):
                continue

            model = getattr(models, attribute_type.__name__)

            if instance := model.get(value):
                filter[attribute] = instance

        return all(
            getattr(self, attribute) and value in getattr(self, attribute)
            for attribute, value in filter.items()
        )

    def __html__(self):
        return self.id
