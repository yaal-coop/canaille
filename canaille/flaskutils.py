from functools import wraps
from flask import session, abort
from canaille.models import User


def current_user():
    if not session.get("user_dn"):
        return None

    if not isinstance(session.get("user_dn"), list):
        del session["user_dn"]
        return None

    dn = session["user_dn"][-1]
    user = User.get(dn=dn)

    if not user:
        try:
            session["user_dn"] = session["user_dn"][:-1]
        except IndexError:
            del session["user_dn"]

    return user


def user_needed():
    def wrapper(view_function):
        @wraps(view_function)
        def decorator(*args, **kwargs):
            user = current_user()
            if not user:
                abort(403)
            return view_function(*args, user=user, **kwargs)

        return decorator

    return wrapper


def moderator_needed():
    def wrapper(view_function):
        @wraps(view_function)
        def decorator(*args, **kwargs):
            user = current_user()
            if not user or not user.moderator:
                abort(403)
            return view_function(*args, user=user, **kwargs)

        return decorator

    return wrapper


def admin_needed():
    def wrapper(view_function):
        @wraps(view_function)
        def decorator(*args, **kwargs):
            user = current_user()
            if not user or not user.admin:
                abort(403)
            return view_function(*args, user=user, **kwargs)

        return decorator

    return wrapper
