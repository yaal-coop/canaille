import datetime

from flask import g
from flask import session


class User:
    def __init__(self, *args, **kwargs):
        self.read = set()
        self.write = set()
        self.permissions = set()
        super().__init__(*args, **kwargs)

    @classmethod
    def get_from_login(cls, login=None, **kwargs):
        raise NotImplementedError()

    def login(self):
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
        try:
            session["user_id"].pop()
            del g.user
            if not session["user_id"]:
                del session["user_id"]
        except (IndexError, KeyError):
            pass

    @property
    def identifier(self):
        """
        Returns a unique value that will be used to identify the user.
        This value will be used in URLs in canaille, so it should be unique and short.
        """
        raise NotImplementedError()

    def has_password(self):
        raise NotImplementedError()

    def check_password(self, password):
        raise NotImplementedError()

    def set_password(self, password):
        raise NotImplementedError()

    def can_read(self, field):
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
    def locked(self):
        return bool(self.lock_date) and self.lock_date < datetime.datetime.now(
            datetime.timezone.utc
        )


class Group:
    @property
    def identifier(self):
        """
        Returns a unique value that will be used to identify the user.
        This value will be used in URLs in canaille, so it should be unique and short.
        """
        raise NotImplementedError()
