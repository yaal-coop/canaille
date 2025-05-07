import datetime
from dataclasses import dataclass

from flask import current_app
from flask import g
from flask import session

from canaille.app import models
from canaille.core.models import User

USER_SESSION = "sessions"


@dataclass
class UserSession:
    user: User | None = None
    last_login_datetime: datetime.datetime | None = None

    @classmethod
    def deserialize(cls, payload):
        user = current_app.backend.instance.get(models.User, payload.get("user"))
        user_is_locked = (
            user and current_app.backend.has_account_lockability() and user.locked
        )
        if not user or user_is_locked:
            return None

        return UserSession(
            user=user,
            last_login_datetime=datetime.datetime.fromisoformat(
                payload["last_login_datetime"]
            )
            if payload.get("last_login_datetime")
            else None,
        )

    def serialize(self):
        return {
            "user": self.user.id,
            "last_login_datetime": self.last_login_datetime.isoformat(),
        }


def current_user_session():
    for payload in session.get(USER_SESSION, [])[::-1]:
        if obj := UserSession.deserialize(payload):
            return obj

        session[USER_SESSION].remove(payload)

    if USER_SESSION in session and not session[USER_SESSION]:
        del session[USER_SESSION]

    return None


def save_user_session():
    session[USER_SESSION][-1] = g.session.serialize()


def login_user(user):
    """Open a session for the user."""
    now = datetime.datetime.now(datetime.timezone.utc)
    obj = UserSession(user=user, last_login_datetime=now)
    g.session = obj
    try:
        previous = (
            session[USER_SESSION]
            if isinstance(session[USER_SESSION], list)
            else [session[USER_SESSION]]
        )
        session[USER_SESSION] = previous + [obj.serialize()]
    except KeyError:
        session[USER_SESSION] = [obj.serialize()]


def logout_user():
    """Close the user session."""
    try:
        session[USER_SESSION].pop()
        if not session[USER_SESSION]:
            del session[USER_SESSION]
    except (IndexError, KeyError):
        pass

    del g.session
