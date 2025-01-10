import logging
from functools import wraps
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from flask import abort
from flask import current_app
from flask import flash
from flask import make_response
from flask import redirect
from flask import request
from flask import url_for
from werkzeug.exceptions import HTTPException
from werkzeug.routing import BaseConverter

from canaille.app.i18n import gettext as _
from canaille.app.session import current_user
from canaille.app.templating import render_template


def user_needed(*args):
    permissions = set(args)

    def wrapper(view_function):
        @wraps(view_function)
        def decorator(*args, **kwargs):
            user = current_user()
            if not user or not user.can(*permissions):
                abort(403)

            if user.has_expired_password():
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


def request_is_boosted() -> bool:
    """Whether the request is boosted with HTMX.

    https://htmx.org/docs/#boosting
    """
    return request.headers.get("HX-Boosted", False)


def request_is_partial() -> bool:
    """Whether the request only updates a subset of the DOM.

    True for form inline validation for instance.
    """
    return request.headers.get("HX-Request", False) and not request_is_boosted()


def render_htmx_template(template, htmx_template=None, **kwargs):
    if request_is_partial():
        if htmx_template:
            template = htmx_template
        else:
            *dirs, file = template.split("/")
            template = "/".join([*dirs, "partial", file])
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


def redirect_to_bp_handlers(app, error):
    """Find and execute blueprint handlers matching an error.

    There is currently no way to make 404 handling generic:
    https://flask.palletsprojects.com/en/stable/errorhandling/#handling
        However, the blueprint cannot handle 404 routing errors because the
        404 occurs at the routing level before the blueprint can be determined.
    """
    for bp in app.blueprints.values():
        if bp.url_prefix and request.path.startswith(bp.url_prefix):
            for type_, handler in bp.error_handler_spec[None][None].items():
                if type_ in (error.code, HTTPException):  # pragma: no branch
                    return make_response(handler(error))
    return None
