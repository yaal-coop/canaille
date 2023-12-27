import datetime
from logging.config import dictConfig

from flask import Flask
from flask import request
from flask import session
from flask_wtf.csrf import CSRFProtect


csrf = CSRFProtect()


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
            "loggers": {
                "faker": {"level": "WARNING"},
            },
            "disable_existing_loggers": False,
        }
    )


def setup_jinja(app):
    app.jinja_env.filters["len"] = len
    app.jinja_env.policies["ext.i18n.trimmed"] = True


def setup_blueprints(app):
    import canaille.core.endpoints

    app.url_map.strict_slashes = False

    app.register_blueprint(canaille.core.endpoints.bp)

    if "OIDC" in app.config:
        import canaille.oidc.endpoints

        app.register_blueprint(canaille.oidc.endpoints.bp)


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
            "debug": app.debug or app.config.get("TESTING", False),
            "has_smtp": "SMTP" in app.config,
            "has_oidc": "OIDC" in app.config,
            "has_password_recovery": app.config.get("ENABLE_PASSWORD_RECOVERY", True),
            "has_registration": app.config.get("ENABLE_REGISTRATION", False),
            "has_account_lockability": app.backend.get().has_account_lockability(),
            "logo_url": app.config.get("LOGO"),
            "favicon_url": app.config.get("FAVICON", app.config.get("LOGO")),
            "website_name": app.config.get("NAME", "Canaille"),
            "user": current_user(),
            "menu": True,
            "is_boosted": request.headers.get("HX-Boosted", False),
            "has_email_confirmation": app.config.get("EMAIL_CONFIRMATION") is True
            or (app.config.get("EMAIL_CONFIRMATION") is None and "SMTP" in app.config),
        }


def setup_flask_converters(app):
    from canaille.app.flask import model_converter
    from canaille.app import models

    for model_name, model_class in models.MODELS.items():
        app.url_map.converters[model_name.lower()] = model_converter(model_class)


def create_app(config=None, validate=True, backend=None):
    from .app.i18n import setup_i18n
    from .app.configuration import setup_config
    from .app.themes import setup_themer
    from .backends import setup_backend

    app = Flask(__name__)
    with app.app_context():
        setup_config(app, config, validate)

    sentry_sdk = setup_sentry(app)
    try:
        setup_logging(app)
        backend = setup_backend(app, backend)
        setup_flask_converters(app)
        setup_blueprints(app)
        setup_jinja(app)
        setup_i18n(app)
        setup_themer(app)
        setup_flask(app)

        if "OIDC" in app.config:
            from .oidc.oauth import setup_oauth

            setup_oauth(app)

    except Exception as exc:  # pragma: no cover
        if sentry_sdk:
            sentry_sdk.capture_exception(exc)
        raise

    return app
