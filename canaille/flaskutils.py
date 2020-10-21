import ldap
from functools import wraps
from flask import session, abort
from canaille.models import User


def current_user():
    if "user_dn" not in session:
        return None

    try:
        return User.get(session["user_dn"])
    except ldap.NO_SUCH_OBJECT:
        return None


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


def admin_needed():
    def wrapper(view_function):
        @wraps(view_function)
        def decorator(*args, **kwargs):
            user = current_user()
            if not user or not user.admin:
                abort(403)
            return view_function(*args, **kwargs)

        return decorator

    return wrapper
