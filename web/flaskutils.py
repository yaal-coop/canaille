from functools import wraps
from flask import session, abort
from web.models import User


def current_user():
    if "user_dn" in session:
        return User.get(session["user_dn"])
    return None


def user_needed():
    def wrapper(view_function):
        @wraps(view_function)
        def decorator(*args, **kwargs):
            if not current_user():
                abort(403)
            return view_function(*args, **kwargs)

        return decorator

    return wrapper


def admin_needed():
    def wrapper(view_function):
        @wraps(view_function)
        def decorator(*args, **kwargs):
            user = current_user()
            if not user:
                abort(403)
            if not user.admin:
                abort(404)
            return view_function(*args, **kwargs)

        return decorator

    return wrapper
