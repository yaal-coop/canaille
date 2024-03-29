import datetime
import sys
from logging.config import dictConfig
from logging.config import fileConfig

from flask import Flask
from flask import request
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


def setup_logging(app):
    conf = app.config["CANAILLE"]["LOGGING"]
    if conf is None:
        log_level = "DEBUG" if app.debug else "INFO"
        dictConfig(
            {
                "version": 1,
                "formatters": {
                    "default": {
                        "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
                    }
                },
                "handlers": {
                    "wsgi": {
                        "class": "logging.StreamHandler",
                        "stream": "ext://flask.logging.wsgi_errors_stream",
                        "formatter": "default",
                    }
                },
                "root": {"level": log_level, "handlers": ["wsgi"]},
                "loggers": {
                    "faker": {"level": "WARNING"},
                    "mail.log": {"level": "WARNING"},
                },
                "disable_existing_loggers": False,
            }
        )

    elif isinstance(conf, dict):
        dictConfig(conf)

    else:
        fileConfig(conf, disable_existing_loggers=False)


def setup_jinja(app):
    app.jinja_env.filters["len"] = len
    app.jinja_env.policies["ext.i18n.trimmed"] = True


def setup_blueprints(app):
    import canaille.core.endpoints

    app.url_map.strict_slashes = False

    app.register_blueprint(canaille.core.endpoints.bp)

    if "CANAILLE_OIDC" in app.config:
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
            "has_smtp": "SMTP" in app.config["CANAILLE"],
            "has_oidc": "CANAILLE_OIDC" in app.config,
            "has_password_recovery": app.config["CANAILLE"]["ENABLE_PASSWORD_RECOVERY"],
            "has_registration": app.config["CANAILLE"]["ENABLE_REGISTRATION"],
            "has_account_lockability": app.backend.get().has_account_lockability(),
            "logo_url": app.config["CANAILLE"]["LOGO"],
            "favicon_url": app.config["CANAILLE"]["FAVICON"]
            or app.config["CANAILLE"]["LOGO"],
            "website_name": app.config["CANAILLE"]["NAME"],
            "user": current_user(),
            "menu": True,
            "is_boosted": request.headers.get("HX-Boosted", False),
            "has_email_confirmation": app.config["CANAILLE"]["EMAIL_CONFIRMATION"]
            is True
            or (
                app.config["CANAILLE"]["EMAIL_CONFIRMATION"] is None
                and "SMTP" in app.config["CANAILLE"]
            ),
        }


def setup_flask_converters(app):
    from canaille.app import models
    from canaille.app.flask import model_converter

    for model_name, model_class in models.MODELS.items():
        app.url_map.converters[model_name.lower()] = model_converter(model_class)


def create_app(config=None, validate=True, backend=None):
    from .app.configuration import setup_config
    from .app.i18n import setup_i18n
    from .app.themes import setup_themer
    from .backends import setup_backend

    app = Flask(__name__)
    with app.app_context():
        if not setup_config(app, config, validate):  # pragma: no cover
            sys.exit(1)

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

        if "CANAILLE_OIDC" in app.config:
            from .oidc.oauth import setup_oauth

            setup_oauth(app)

    except Exception as exc:  # pragma: no cover
        if sentry_sdk:
            sentry_sdk.capture_exception(exc)
        raise

    return app
