import datetime
import inspect
import typing
from collections import ChainMap
from typing import Annotated
from typing import ClassVar
from typing import Union
from typing import get_origin
from typing import get_type_hints

from canaille.app import classproperty
from canaille.app import models
from canaille.backends import Backend

try:
    from types import UnionType  # type: ignore

    UNION_TYPES = [Union, UnionType]
except ImportError:
    # Python 3.9 has no UnionType
    UNION_TYPES = [Union]


class Model:
    """The model abstract class.

    It details all the common attributes shared by every models.
    """

    id: str | None = None
    """A unique identifier for a SCIM resource as defined by the service
    provider. Id will be :data:`None` until the
    ``Backend.save`` method is called.

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

    created: datetime.datetime | None = None
    """The :class:`~datetime.datetime` that the resource was added to the
    service provider."""

    last_modified: datetime.datetime | None = None
    """The most recent :class:`~datetime.datetime` that the details of this
    resource were updated at the service provider.

    If this resource has never been modified since its initial creation,
    the value MUST be the same as the value of :attr:`~canaille.backends.models.Model.created`.
    """

    _attributes: ClassVar[list[str] | None] = None

    @classproperty
    def attributes(cls):
        if not cls._attributes:
            annotations = ChainMap(
                *(
                    get_type_hints(klass, include_extras=True)
                    for klass in reversed(cls.__mro__)
                    if issubclass(klass, Model)
                )
            )
            # only keep types that are not ClassVar
            cls._attributes = {
                key: value
                for key, value in annotations.items()
                if get_origin(value) is not ClassVar
            }
        return cls._attributes

    def __html__(self):
        return self.id

    @property
    def identifier(self):
        """Returns a unique value that will be used to identify the model
        instance.

        This value will be used in URLs in canaille, so it should be
        unique and short.
        """
        return getattr(self, self.identifier_attribute)


class BackendModel:
    """The backend model abstract class.

    It details all the methods and attributes that are expected to be
    implemented for every model and for every backend.
    """

    @classmethod
    def get_model_annotations(cls, attribute):
        annotations = cls.attributes[attribute]

        # Extract the list type from list annotations
        attribute_type = (
            typing.get_args(annotations)[0]
            if typing.get_origin(annotations) is list
            else annotations
        )

        # Extract the Optional and Union type
        attribute_type = (
            typing.get_args(attribute_type)[0]
            if typing.get_origin(attribute_type) in UNION_TYPES
            else attribute_type
        )

        # Extract the Annotated annotation
        attribute_type, metadata = (
            typing.get_args(attribute_type)
            if typing.get_origin(attribute_type) == Annotated
            else (attribute_type, None)
        )

        if not inspect.isclass(attribute_type) or not issubclass(attribute_type, Model):
            return None, None

        if not metadata:
            return attribute_type, None

        return attribute_type, metadata.get("backref")

    def match_filter(self, filter):
        if filter is None:
            return True

        if isinstance(filter, list):
            return any(self.match_filter(subfilter) for subfilter in filter)

        # If attribute are models, resolve the instance
        filter = filter.copy()
        for attribute, value in filter.items():
            model, _ = self.get_model_annotations(attribute)

            if not model or isinstance(value, Model):
                continue

            backend_model = getattr(models, model.__name__)

            if instance := Backend.instance.get(backend_model, value):
                filter[attribute] = instance

        return all(
            getattr(self, attribute) and value in getattr(self, attribute)
            for attribute, value in filter.items()
        )
