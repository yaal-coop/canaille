import datetime
import logging
from functools import wraps
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from canaille.models import User
from flask import abort
from flask import current_app
from flask import render_template
from flask import session
from flask_babel import gettext as _


def current_user():
    for dn in session.get("user_id", [])[::-1]:
        user = User.get(dn=dn)
        if user:
            return user

        session["user_id"].remove(dn)

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


def permissions_needed(*args):
    permissions = set(args)

    def wrapper(view_function):
        @wraps(view_function)
        def decorator(*args, **kwargs):
            user = current_user()
            if not user or not permissions.issubset(user.permissions):
                abort(403)
            return view_function(*args, user=user, **kwargs)

        return decorator

    return wrapper


def smtp_needed():
    def wrapper(view_function):
        @wraps(view_function)
        def decorator(*args, **kwargs):
            if "SMTP" in current_app.config:
                return view_function(*args, **kwargs)

            message = _("No SMTP server has been configured")
            logging.warning(message)
            return (
                render_template(
                    "error.html",
                    error=500,
                    icon="tools",
                    debug=current_app.config.get("DEBUG", False),
                    description=message,
                ),
                500,
            )

        return decorator

    return wrapper


def timestamp(dt):
    return datetime.datetime.timestamp(dt)


def set_parameter_in_url_query(url, **kwargs):
    split = list(urlsplit(url))
    pairs = split[3].split("&")
    parameters = {pair.split("=")[0]: pair.split("=")[1] for pair in pairs if pair}
    parameters = {**parameters, **kwargs}
    split[3] = "&".join(f"{key}={value}" for key, value in parameters.items())
    return urlunsplit(split)
