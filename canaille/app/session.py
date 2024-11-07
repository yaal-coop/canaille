from flask import current_app
from flask import g
from flask import session

from canaille.app import models


def current_user():
    if "user" in g:
        return g.user

    for user_id in session.get("user_id", [])[::-1]:
        user = current_app.backend.instance.get(models.User, user_id)
        if user and (
            not current_app.backend.has_account_lockability() or not user.locked
        ):
            g.user = user
            return g.user

        session["user_id"].remove(user_id)

    if "user_id" in session and not session["user_id"]:
        del session["user_id"]

    return None


def login_user(user):
    """Open a session for the user."""
    g.user = user
    try:
        previous = (
            session["user_id"]
            if isinstance(session["user_id"], list)
            else [session["user_id"]]
        )
        session["user_id"] = previous + [user.id]
    except KeyError:
        session["user_id"] = [user.id]


def logout_user():
    """Close the user session."""
    try:
        session["user_id"].pop()
        del g.user
        if not session["user_id"]:
            del session["user_id"]
    except (IndexError, KeyError):
        pass
