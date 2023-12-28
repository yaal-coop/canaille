from collections import ChainMap

from canaille.app import classproperty


class Model:
    """Model abstract class."""

    @classproperty
    def attributes(cls):
        return ChainMap(
            *(c.__annotations__ for c in cls.__mro__ if "__annotations__" in c.__dict__)
        )

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
        """Works like :meth:`~canaille.backends.models.query` but attribute
        values loosely be matched."""
        raise NotImplementedError()

    @classmethod
    def get(cls, identifier=None, **kwargs):
        """Works like :meth:`~canaille.backends.models.query` but return only
        one element or :const:`None` if no item is matching."""
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
