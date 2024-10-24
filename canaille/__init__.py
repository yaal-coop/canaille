import datetime
import logging
import sys
from logging.config import dictConfig
from logging.config import fileConfig

from flask import Flask
from flask import request
from flask import session
from flask_wtf.csrf import CSRFProtect

from canaille.app.forms import password_strength_calculator

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

    security_level_name = "SECURITY"
    if not hasattr(logging, security_level_name):
        addLoggingLevel(security_level_name, logging.INFO + 5)

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
    app.jinja_env.filters["password_strength"] = password_strength_calculator
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
            "logo_url": app.config["CANAILLE"]["LOGO"],
            "favicon_url": app.config["CANAILLE"]["FAVICON"]
            or app.config["CANAILLE"]["LOGO"],
            "website_name": app.config["CANAILLE"]["NAME"],
            "user": current_user(),
            "menu": True,
            "is_boosted": request.headers.get("HX-Boosted", False),
            "features": app.features,
        }


def setup_flask_converters(app):
    from canaille.app import models
    from canaille.app.flask import model_converter

    for model_name, model_class in models.MODELS.items():
        app.url_map.converters[model_name.lower()] = model_converter(model_class)


def create_app(
    config=None, validate=True, backend=None, env_file=".env", env_prefix=""
):
    from .app.configuration import setup_config
    from .app.features import setup_features
    from .app.i18n import setup_i18n
    from .app.themes import setup_themer
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
        backend = setup_backend(app, backend)
        setup_features(app)
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


def addLoggingLevel(levelName, levelNum, methodName=None):
    """Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present

    Example
    -------
    >>> addLoggingLevel("TRACE", logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace("that worked")
    >>> logging.trace("so did this")
    >>> logging.TRACE
    5
    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
        raise AttributeError(f"{levelName} already defined in logging module")
    if hasattr(logging, methodName):
        raise AttributeError(f"{methodName} already defined in logging module")
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError(f"{methodName} already defined in logger class")

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)

    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)
