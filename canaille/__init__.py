import datetime
import os
from logging.config import dictConfig

from flask import Flask
from flask import g
from flask import request
from flask import session
from flask_themer import FileSystemThemeLoader
from flask_themer import render_template
from flask_themer import Themer
from flask_wtf.csrf import CSRFProtect


csrf = CSRFProtect()


def setup_backend(app, backend):
    from .backends.ldap.backend import Backend

    if not backend:
        backend = Backend(app.config)
        backend.init_app(app)

    with app.app_context():
        g.backend = backend
        app.backend = backend

    if app.debug:  # pragma: no cover
        backend.install(app.config)


def setup_sentry(app):  # pragma: no cover
    if not app.config.get("SENTRY_DSN"):
        return None

    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

    except Exception:
        return None

    sentry_sdk.init(dsn=app.config["SENTRY_DSN"], integrations=[FlaskIntegration()])
    return sentry_sdk


def setup_logging(app):
    log_level = app.config.get("LOGGING", {}).get("LEVEL", "WARNING")
    if not app.config.get("LOGGING", {}).get("PATH"):
        handler = {
            "class": "logging.StreamHandler",
            "stream": "ext://flask.logging.wsgi_errors_stream",
            "formatter": "default",
        }
    else:
        handler = {
            "class": "logging.handlers.WatchedFileHandler",
            "filename": app.config["LOGGING"]["PATH"],
            "formatter": "default",
        }

    dictConfig(
        {
            "version": 1,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                }
            },
            "handlers": {"wsgi": handler},
            "root": {"level": log_level, "handlers": ["wsgi"]},
            "disable_existing_loggers": False,
        }
    )


def setup_jinja(app):
    app.jinja_env.filters["len"] = len
    app.jinja_env.policies["ext.i18n.trimmed"] = True


def setup_themer(app):
    additional_themes_dir = (
        os.path.dirname(app.config["THEME"])
        if app.config.get("THEME") and os.path.exists(app.config["THEME"])
        else None
    )
    themer = Themer(
        app,
        loaders=[FileSystemThemeLoader(additional_themes_dir)]
        if additional_themes_dir
        else None,
    )

    @themer.current_theme_loader
    def get_current_theme():
        # if config['THEME'] may be a theme name or an absolute path
        return app.config.get("THEME", "default").split("/")[-1]


def setup_blueprints(app):
    import canaille.core.account
    import canaille.core.admin
    import canaille.core.groups
    import canaille.oidc.blueprints

    app.url_map.strict_slashes = False

    app.register_blueprint(canaille.core.account.bp)
    app.register_blueprint(canaille.core.admin.bp)
    app.register_blueprint(canaille.core.groups.bp)
    app.register_blueprint(canaille.oidc.blueprints.bp)


def setup_flask(app):
    csrf.init_app(app)

    @app.before_request
    def make_session_permanent():
        session.permanent = True
        app.permanent_session_lifetime = datetime.timedelta(days=365)

    @app.context_processor
    def global_processor():
        from canaille.app.flask import current_user

        return {
            "debug": app.config.get("DEBUG", False) or app.config.get("TESTING", False),
            "has_smtp": "SMTP" in app.config,
            "has_password_recovery": app.config.get("ENABLE_PASSWORD_RECOVERY", True),
            "has_account_lockability": app.backend.get().has_account_lockability(),
            "logo_url": app.config.get("LOGO"),
            "favicon_url": app.config.get("FAVICON", app.config.get("LOGO")),
            "website_name": app.config.get("NAME", "Canaille"),
            "user": current_user(),
            "menu": True,
            "is_boosted": request.headers.get("HX-Boosted", False),
        }

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", description=error, error_code=400), 400

    @app.errorhandler(403)
    def unauthorized(error):
        return render_template("error.html", description=error, error_code=403), 403

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("error.html", description=error, error_code=404), 404

    @app.errorhandler(500)
    def server_error(error):  # pragma: no cover
        return render_template("error.html", description=error, error_code=500), 500


def setup_flask_converters(app):
    from canaille.app.flask import model_converter
    from canaille.app import models

    app.url_map.converters["user"] = model_converter(models.User)
    app.url_map.converters["group"] = model_converter(models.Group)
    app.url_map.converters["client"] = model_converter(models.Client)
    app.url_map.converters["token"] = model_converter(models.Token)
    app.url_map.converters["authorizationcode"] = model_converter(
        models.AuthorizationCode
    )
    app.url_map.converters["consent"] = model_converter(models.Consent)


def create_app(config=None, validate=True, backend=None):
    from .oidc.oauth import setup_oauth
    from .app.i18n import setup_i18n
    from .app.configuration import setup_config

    app = Flask(__name__)
    setup_config(app, config, validate)

    sentry_sdk = setup_sentry(app)
    try:
        setup_logging(app)
        setup_backend(app, backend)
        setup_oauth(app)
        setup_flask_converters(app)
        setup_blueprints(app)
        setup_jinja(app)
        setup_i18n(app)
        setup_themer(app)
        setup_flask(app)

    except Exception as exc:  # pragma: no cover
        if sentry_sdk:
            sentry_sdk.capture_exception(exc)
        raise

    return app
