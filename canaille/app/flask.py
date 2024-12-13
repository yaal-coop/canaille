import datetime
import logging
from functools import wraps
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from flask import abort
from flask import current_app
from flask import flash
from flask import redirect
from flask import request
from flask import url_for
from pytz import UTC
from werkzeug.routing import BaseConverter

from canaille.app.i18n import gettext as _
from canaille.app.session import current_user
from canaille.app.themes import render_template


def get_today_datetime():
    return UTC.localize(datetime.datetime.now())  # pragma: no cover


def expired_password_needed():
    """Check if password has not expired."""

    def wrapper(view_function):
        @wraps(view_function)
        def decorator(*args, **kwargs):
            if current_user():
                user = current_user()

                last_update = user.password_last_update or get_today_datetime()

                password_expiration = current_app.config["CANAILLE"][
                    "PASSWORD_LIFETIME"
                ]
                if (
                    password_expiration is None
                    or password_expiration == 0
                    or password_expiration == datetime.timedelta(microseconds=0)
                    or last_update + password_expiration >= get_today_datetime()
                ):
                    abort(403)
            return view_function(*args, **kwargs)

        return decorator

    return wrapper


def user_needed(*args):
    permissions = set(args)

    def wrapper(view_function):
        @wraps(view_function)
        def decorator(*args, **kwargs):
            user = current_user()
            if not user or not user.can(*permissions):
                abort(403)

            last_update = user.password_last_update or get_today_datetime()

            password_expiration = current_app.config["CANAILLE"]["PASSWORD_LIFETIME"]
            if (
                password_expiration is not None
                and password_expiration != 0
                and password_expiration != datetime.timedelta(milliseconds=0)
                and last_update + password_expiration < get_today_datetime()
            ):
                flash(
                    _("Your password has expired, please choose a new password."),
                    "info",
                )
                return redirect(
                    url_for(
                        "core.account.reset",
                        user=user,
                    )
                )

            return view_function(*args, user=user, **kwargs)

        return decorator

    return wrapper


def smtp_needed():
    def wrapper(view_function):
        @wraps(view_function)
        def decorator(*args, **kwargs):
            if current_app.features.has_smtp:
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
            return instance.identifier or instance.id

        def to_python(self, identifier):
            current_app.backend.setup()
            instance = current_app.backend.get(model, identifier)
            if self.required and not instance:
                abort(404)

            return instance

    return ModelConverter
