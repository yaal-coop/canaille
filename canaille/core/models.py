import datetime
from typing import Optional

from flask import g
from flask import session


class User:
    """
    User model, based on the `SCIM User schema <https://datatracker.ietf.org/doc/html/rfc7643#section-4.1>`_
    """

    def __init__(self, *args, **kwargs):
        self.read = set()
        self.write = set()
        self.permissions = set()
        super().__init__(*args, **kwargs)

    @classmethod
    def get_from_login(cls, login=None, **kwargs) -> Optional["User"]:
        raise NotImplementedError()

    def login(self):
        """
        Opens a session for the user.
        """
        g.user = self
        try:
            previous = (
                session["user_id"]
                if isinstance(session["user_id"], list)
                else [session["user_id"]]
            )
            session["user_id"] = previous + [self.id]
        except KeyError:
            session["user_id"] = [self.id]

    @classmethod
    def logout(self):
        """
        Closes the user session.
        """
        try:
            session["user_id"].pop()
            del g.user
            if not session["user_id"]:
                del session["user_id"]
        except (IndexError, KeyError):
            pass

    def has_password(self) -> bool:
        """
        Checks wether a password has been set for the user.
        """
        raise NotImplementedError()

    def check_password(self, password: str) -> bool:
        """
        Checks if the password matches the user password in the database.
        """
        raise NotImplementedError()

    def set_password(self, password: str):
        """
        Sets a password for the user.
        """
        raise NotImplementedError()

    def can_read(self, field: str):
        return field in self.read | self.write

    @property
    def preferred_email(self):
        return self.emails[0] if self.emails else None

    def __getattr__(self, name):
        if name.startswith("can_") and name != "can_read":
            permission = name[4:]
            return permission in self.permissions

        return super().__getattr__(name)

    @property
    def locked(self) -> bool:
        """
        Wether the user account has been locked or has expired.
        """
        return bool(self.lock_date) and self.lock_date < datetime.datetime.now(
            datetime.timezone.utc
        )


class Group:
    """
    User model, based on the `SCIM Group schema <https://datatracker.ietf.org/doc/html/rfc7643#section-4.2>`_
    """
