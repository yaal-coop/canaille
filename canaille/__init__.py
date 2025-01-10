import datetime
import sys

from flask import Flask
from flask import session
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()


def setup_sentry(app):  # pragma: no cover
    if not app.config["CANAILLE"]["SENTRY_DSN"]:
        return None

    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

    except Exception:
        return None

    sentry_sdk.init(
        dsn=app.config["CANAILLE"]["SENTRY_DSN"], integrations=[FlaskIntegration()]
    )
    return sentry_sdk


def setup_blueprints(app):
    import canaille.core.endpoints

    app.url_map.strict_slashes = False

    app.register_blueprint(canaille.core.endpoints.bp)

    if app.features.has_oidc:
        import canaille.oidc.endpoints

        app.register_blueprint(canaille.oidc.endpoints.bp)

    if app.features.has_scim_server:
        import canaille.scim.endpoints

        app.register_blueprint(canaille.scim.endpoints.bp)


def setup_flask(app):
    from canaille.app.templating import render_template

    csrf.init_app(app)

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


def create_app(
    config: dict = None,
    validate: bool = True,
    backend=None,
    init_backend=None,
    env_file: str = None,
    env_prefix: str = "",
):
    """Application entry point.

    :param config: A configuration dict. This will take priority over any other configuration method.
    :param validate: Whether to validate or not the configuration.
    :param backend: An optional backend to force. If unset backend will be initialized according to the configuration.
    :param env_file: The path to an environment var file in which configuration can be loaded.
    :param env_prefix: The prefix to configuration environment vars.
    """
    from .app.configuration import setup_config
    from .app.features import setup_features
    from .app.i18n import setup_i18n
    from .app.logging import setup_logging
    from .app.templating import setup_jinja
    from .app.templating import setup_themer
    from .backends import setup_backend

    app = Flask(__name__)
    with app.app_context():
        if not setup_config(
            app=app,
            config=config,
            test_config=validate,
            env_file=env_file,
            env_prefix=env_prefix,
        ):  # pragma: no cover
            sys.exit(1)

    sentry_sdk = setup_sentry(app)
    try:
        setup_logging(app)
        backend = setup_backend(app, backend, init_backend)
        setup_features(app)
        setup_flask_converters(app)
        setup_blueprints(app)
        setup_jinja(app)
        setup_i18n(app)
        setup_themer(app)
        setup_flask(app)

        if app.features.has_oidc:
            from .oidc.oauth import setup_oauth

            setup_oauth(app)

    except Exception as exc:  # pragma: no cover
        if sentry_sdk:
            sentry_sdk.capture_exception(exc)
        raise

    return app
