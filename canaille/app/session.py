import datetime

from flask import current_app
from flask import g
from flask import session

from canaille.app import models


def current_user():
    if "user" in g:
        return g.user

    for user_id, login_datetime in session.get("user_id", [])[::-1]:
        user = current_app.backend.instance.get(models.User, user_id)
        if user and (
            not current_app.backend.has_account_lockability() or not user.locked
        ):
            g.user = user
            g.last_login_datetime = datetime.datetime.fromisoformat(login_datetime)
            return g.user

        session["user_id"].remove((user_id, login_datetime))

    if "user_id" in session and not session["user_id"]:
        del session["user_id"]

    return None


def current_user_login_datetime() -> datetime.datetime | None:
    if "last_login_datetime" in g:
        return g.last_login_datetime

    for user_id, login_datetime in session.get("user_id", [])[::-1]:
        user = current_app.backend.instance.get(models.User, user_id)
        if user and (
            not current_app.backend.has_account_lockability() or not user.locked
        ):
            g.user = user
            g.last_login_datetime = datetime.datetime.fromisoformat(login_datetime)
            return g.last_login_datetime

        session["user_id"].remove((user_id, login_datetime))

    if "user_id" in session and not session["user_id"]:
        del session["user_id"]

    return None


def login_user(user):
    """Open a session for the user."""
    g.user = user
    g.last_login_datetime = datetime.datetime.now(datetime.timezone.utc)
    try:
        previous = (
            session["user_id"]
            if isinstance(session["user_id"], list)
            else [session["user_id"]]
        )
        session["user_id"] = previous + [(user.id, g.last_login_datetime.isoformat())]
    except KeyError:
        session["user_id"] = [(user.id, g.last_login_datetime.isoformat())]


def logout_user():
    """Close the user session."""
    try:
        session["user_id"].pop()
        if not session["user_id"]:
            del session["user_id"]
    except (IndexError, KeyError):
        pass

    if "user" in g:
        del g.user

    if "last_login_datetime" in g:
        del g.last_login_datetime
