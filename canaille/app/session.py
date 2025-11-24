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


@dataclass
class UserSession:
    user: User | None = None
    last_login_datetime: datetime.datetime | None = None
    authentication_methods: list[str] | None = None

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
            authentication_methods=payload.get("authentication_methods"),
        )

    def serialize(self):
        payload = {
            "user": self.user.id,
            "last_login_datetime": self.last_login_datetime.isoformat(),
        }
        if self.authentication_methods is not None:
            payload["authentication_methods"] = self.authentication_methods
        return payload


def current_user_session():
    for payload in session.get(USER_SESSION, []):
        if obj := UserSession.deserialize(payload):
            return obj

        session[USER_SESSION].remove(payload)

    if USER_SESSION in session and not session[USER_SESSION]:
        del session[USER_SESSION]

    return None


def save_user_session() -> None:
    session[USER_SESSION][0] = g.session.serialize()


def login_user(user, remember: bool = True) -> None:
    """Open a session for the user."""
    now = datetime.datetime.now(datetime.timezone.utc)
    authentication_methods = g.auth.achieved if hasattr(g, "auth") and g.auth else None
    obj = UserSession(
        user=user,
        last_login_datetime=now,
        authentication_methods=authentication_methods,
    )
    g.session = obj
    try:
        previous = (
            session[USER_SESSION]
            if isinstance(session[USER_SESSION], list)
            else [session[USER_SESSION]]
        )

        existing_index = _find_session_index(previous, user.id)
        if existing_index is not None:
            previous.pop(existing_index)

        session[USER_SESSION] = [obj.serialize()] + previous
    except KeyError:
        session[USER_SESSION] = [obj.serialize()]

    session.permanent = remember
    if remember:
        add_to_login_history(user.user_name)


def _find_session_index(sessions, user_id):
    """Find index of session for given user_id, or None if not found."""
    for i, payload in enumerate(sessions):
        if user_session := UserSession.deserialize(payload):
            if user_session.user.id == user_id:
                return i
    return None


def logout_user(user_id: str | None = None) -> bool:
    """Close a user session.

    If user_id is None, closes the current user session (position 0).
    Otherwise, closes the session for the specified user.
    """
    sessions = session.get(USER_SESSION, [])
    if not sessions:
        return False

    target_index = 0 if user_id is None else _find_session_index(sessions, user_id)

    if target_index is None:
        return False

    sessions.pop(target_index)
    if sessions:
        session[USER_SESSION] = sessions
    else:
        del session[USER_SESSION]

    if target_index == 0 and hasattr(g, "session"):
        del g.session

    return True


def logout_all_users() -> None:
    """Close all user sessions."""
    session.pop(USER_SESSION, None)
    if hasattr(g, "session"):
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
    session_lifetime = current_app.config["PERMANENT_SESSION_LIFETIME"]

    response.set_cookie(
        LOGIN_HISTORY_COOKIE,
        cookie_value,
        max_age=int(session_lifetime.total_seconds()),
        secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
        httponly=True,
        samesite="Lax",
    )

    return response


def add_to_login_history(identifier) -> None:
    """Add a user identifier to the login history.

    The identifier is moved to the front if already present, ensuring
    the most recently used accounts appear first. The list is capped
    at MAX_LOGIN_HISTORY entries.
    """
    if not identifier:
        return

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


def is_user_in_login_history(user_name) -> bool:
    """Check if a user identifier is in the login history."""
    identifiers = session.get(LOGIN_HISTORY)
    if identifiers is None:
        identifiers = _get_login_history_from_cookie()

    return user_name in identifiers


def remove_from_login_history(identifier) -> None:
    """Remove a user identifier from the login history."""
    if not identifier:
        return

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


def get_active_sessions():
    """Get all active user sessions."""
    return [
        user_session
        for payload in session.get(USER_SESSION, [])
        if (user_session := UserSession.deserialize(payload))
    ]


def user_session_opened(user_id: str) -> bool:
    """Check if a session exists for the given user."""
    sessions = session.get(USER_SESSION, [])
    return _find_session_index(sessions, user_id) is not None


def switch_to_session(user_id: str) -> None:
    """Switch to an existing session by moving it to the top of the stack."""
    sessions = session.get(USER_SESSION, [])
    if not sessions:
        return

    target_index = _find_session_index(sessions, user_id)
    if target_index is None:
        return

    target_session = sessions.pop(target_index)
    sessions.insert(0, target_session)
    session[USER_SESSION] = sessions
    g.session = UserSession.deserialize(target_session)
