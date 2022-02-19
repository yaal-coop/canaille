import datetime
import logging
from functools import wraps

import ldap
from canaille.models import User
from flask import abort
from flask import current_app
from flask import render_template
from flask import session
from flask_babel import gettext as _


def current_user():
    if not session.get("user_dn"):
        return None

    if not isinstance(session.get("user_dn"), list):
        del session["user_dn"]
        return None

    dn = session["user_dn"][-1]
    try:
        user = User.get(dn=dn)
    except ldap.LDAPError:
        return None

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
