import logging
from functools import wraps
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from canaille.app import models
from canaille.app.i18n import gettext as _
from canaille.app.themes import render_template
from flask import abort
from flask import current_app
from flask import g
from flask import request
from flask import session
from werkzeug.routing import BaseConverter


def current_user():
    if "user" in g:
        return g.user

    for user_id in session.get("user_id", [])[::-1]:
        user = models.User.get(id=user_id)
        if user and (
            not current_app.backend.has_account_lockability() or not user.locked
        ):
            g.user = user
            return g.user

        session["user_id"].remove(user_id)

    return None


def login_user(user):
    """Opens a session for the user."""
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
    """Closes the user session."""
    try:
        session["user_id"].pop()
        del g.user
        if not session["user_id"]:
            del session["user_id"]
    except (IndexError, KeyError):
        pass


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
                    error_code=500,
                    icon="tools",
                    description=message,
                ),
                500,
            )

        return decorator

    return wrapper


def set_parameter_in_url_query(url, **kwargs):
    split = list(urlsplit(url))
    pairs = split[3].split("&")
    parameters = {pair.split("=")[0]: pair.split("=")[1] for pair in pairs if pair}
    parameters = {**parameters, **kwargs}
    split[3] = "&".join(f"{key}={value}" for key, value in parameters.items())
    return urlunsplit(split)


def request_is_htmx():
    return request.headers.get("HX-Request", False) and not request.headers.get(
        "HX-Boosted", False
    )


def render_htmx_template(template, htmx_template=None, **kwargs):
    template = (
        (htmx_template or f"partial/{template}") if request_is_htmx() else template
    )
    return render_template(template, **kwargs)


def model_converter(model):
    class ModelConverter(BaseConverter):
        def __init__(self, *args, required=True, **kwargs):
            self.required = required
            super().__init__(self, *args, **kwargs)

        def to_url(self, instance):
            return instance.identifier

        def to_python(self, identifier):
            current_app.backend.setup()
            instance = model.get(identifier)
            if self.required and not instance:
                abort(404)

            return instance

    return ModelConverter
