import datetime
import logging
import re
from functools import wraps

from flask import abort
from flask import current_app
from flask import flash
from flask import make_response
from flask import redirect
from flask import request
from flask import session
from flask import url_for
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from werkzeug.exceptions import HTTPException
from werkzeug.routing import BaseConverter

from canaille.app.i18n import gettext as _
from canaille.app.session import current_user
from canaille.app.templating import render_template

csrf = CSRFProtect()
cache = Cache()


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


def partial_request_trigger() -> str | None:
    """Return the name of the form element that triggered the HTMX request."""
    base_name = request.headers.get("HX-Trigger-Name")
    return re.sub("-[0-9]+$", "", base_name) if base_name else base_name


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


def setup_flask_blueprints(app):
    import canaille.core.endpoints

    app.url_map.strict_slashes = False

    app.register_blueprint(canaille.core.endpoints.bp)

    if app.features.has_oidc:  # pragma: no branch
        import canaille.oidc.endpoints

        app.register_blueprint(canaille.oidc.endpoints.bp)

    if app.features.has_scim_server:  # pragma: no branch
        import canaille.scim.endpoints

        app.register_blueprint(canaille.scim.endpoints.bp)


def setup_flask(app):
    from canaille.app.templating import render_template

    csrf.init_app(app)
    cache.init_app(app)

    @app.before_request
    def make_session_permanent():
        session.permanent = True
        app.permanent_session_lifetime = datetime.timedelta(days=365)

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", description=error, error_code=400), 400

    @app.errorhandler(403)
    def unauthorized(error):
        return render_template("error.html", description=error, error_code=403), 403

    @app.errorhandler(404)
    def page_not_found(error):
        from canaille.app.flask import redirect_to_bp_handlers

        return redirect_to_bp_handlers(app, error) or render_template(
            "error.html", description=error, error_code=404
        ), 404

    @app.errorhandler(500)
    def server_error(error):  # pragma: no cover
        return render_template("error.html", description=error, error_code=500), 500


def setup_flask_converters(app):
    from canaille.app import models
    from canaille.app.flask import model_converter

    for model_name, model_class in models.MODELS.items():
        app.url_map.converters[model_name.lower()] = model_converter(model_class)
