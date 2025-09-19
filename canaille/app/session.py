import datetime
from dataclasses import dataclass

from flask import current_app
from flask import g
from flask import request
from flask import session
from itsdangerous import BadSignature
from itsdangerous.url_safe import URLSafeSerializer

from canaille.app import models
from canaille.core.models import User

USER_SESSION = "sessions"
LOGIN_HISTORY = "login_history"
LOGIN_HISTORY_COOKIE = "canaille_login_history"
MAX_LOGIN_HISTORY = 6
SESSION_LIFETIME = datetime.timedelta(days=365)


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


def login_user(user, remember: bool = True):
    """Open a session for the user.

    :param user: The user to log in
    :param remember: Whether to create a permanent session and add to login history
    """
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

    session.permanent = remember
    if remember:
        current_app.permanent_session_lifetime = SESSION_LIFETIME
        add_to_login_history(user.user_name)


def logout_user():
    """Close the user session."""
    try:
        session[USER_SESSION].pop()
        if not session[USER_SESSION]:
            del session[USER_SESSION]
    except (IndexError, KeyError):
        pass

    del g.session


def _get_login_history_from_cookie():
    """Get login history from secure cookie."""
    cookie_value = request.cookies.get(LOGIN_HISTORY_COOKIE)
    if not cookie_value:
        return []

    try:
        serializer = URLSafeSerializer(current_app.secret_key)
        data = serializer.loads(cookie_value)
        return data if isinstance(data, list) else []
    except (BadSignature, ValueError, TypeError):
        return []


def _set_login_history_cookie(login_history, response):
    """Set login history in secure cookie."""
    serializer = URLSafeSerializer(current_app.secret_key)
    cookie_value = serializer.dumps(login_history)

    response.set_cookie(
        LOGIN_HISTORY_COOKIE,
        cookie_value,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
        httponly=True,
        samesite="Lax",
    )

    return response


def add_to_login_history(identifier):
    """Add a user identifier to the login history.

    The identifier is moved to the front if already present, ensuring
    the most recently used accounts appear first. The list is capped
    at MAX_LOGIN_HISTORY entries.

    :param identifier: The user identifier or username to remember
    """
    if not identifier:
        return

    # Use existing data from g if available (for tests), otherwise get from cookie
    login_history = getattr(g, "login_history_needs_update", None)
    if login_history is None:
        login_history = _get_login_history_from_cookie()

    if identifier in login_history:
        login_history.remove(identifier)

    login_history.insert(0, identifier)
    login_history = login_history[:MAX_LOGIN_HISTORY]

    session[LOGIN_HISTORY] = login_history
    g.login_history_needs_update = login_history


def get_login_history():
    """Retrieve the list of previously logged-in users from login history.

    Fetches user objects for stored identifiers, filtering out
    deleted or locked accounts. Uses get_user_from_login for
    consistent lookup logic.

    :return: List of User objects that are still valid
    """
    from canaille.core.auth import get_user_from_login

    identifiers = session.get(LOGIN_HISTORY)
    if identifiers is None:
        identifiers = _get_login_history_from_cookie()
        session[LOGIN_HISTORY] = identifiers

    users = []
    for identifier in identifiers:
        user = get_user_from_login(identifier)
        if user and (
            not current_app.backend.has_account_lockability() or not user.locked
        ):
            users.append(user)

    return users


def is_user_in_login_history(user_name):
    """Check if a user identifier is in the login history.

    :param user_name: The username/identifier to check
    :return: True if the user is in login history, False otherwise
    """
    identifiers = session.get(LOGIN_HISTORY)
    if identifiers is None:
        identifiers = _get_login_history_from_cookie()

    return user_name in identifiers


def remove_from_login_history(identifier):
    """Remove a user identifier from the login history.

    :param identifier: The username/identifier to remove
    """
    if not identifier:
        return

    # Use existing data from g if available (for tests), otherwise get from cookie
    login_history = getattr(g, "login_history_needs_update", None)
    if login_history is None:
        login_history = _get_login_history_from_cookie()

    if identifier in login_history:
        login_history.remove(identifier)

        if login_history:
            session[LOGIN_HISTORY] = login_history
        else:
            session.pop(LOGIN_HISTORY, None)

        g.login_history_needs_update = login_history
