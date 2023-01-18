import datetime
import os
from logging.config import dictConfig

import toml
from flask import Flask
from flask import g
from flask import request
from flask import session
from flask_babel import Babel
from flask_babel import get_locale
from flask_themer import FileSystemThemeLoader
from flask_themer import render_template
from flask_themer import Themer

from .i18n import available_language_codes
from .ldap_backend.backend import init_backend
from .oidc.oauth import setup_oauth


def setup_config(app, config=None, validate=True):
    import canaille.configuration

    app.config.from_mapping(
        {
            "SESSION_COOKIE_NAME": "canaille",
            "OAUTH2_REFRESH_TOKEN_GENERATOR": True,
            "OAUTH2_ACCESS_TOKEN_GENERATOR": "canaille.oidc.oauth.generate_access_token",
        }
    )
    if config:
        app.config.from_mapping(config)
    elif "CONFIG" in os.environ:
        app.config.from_mapping(toml.load(os.environ.get("CONFIG")))
    else:
        raise Exception(
            "No configuration file found. "
            "Either create conf/config.toml or set the 'CONFIG' variable environment."
        )

    if app.debug and "JWT" in app.config:  # pragma: no cover
        import canaille.oidc.installation

        canaille.oidc.installation.setup_keypair(app.config)

    if validate:
        canaille.configuration.validate(app.config)


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
    from .flaskutils import timestamp

    app.jinja_env.filters["len"] = len
    app.jinja_env.filters["timestamp"] = timestamp


def setup_i18n(app):
    babel = Babel(app)

    @app.before_request
    def before_request():
        g.available_language_codes = available_language_codes(babel)

    @babel.localeselector
    def get_locale():
        from .flaskutils import current_user

        user = current_user()
        available_language_codes = getattr(g, "available_language_codes", [])
        if user is not None and user.preferredLanguage in available_language_codes:
            return user.preferredLanguage

        if app.config.get("LANGUAGE"):
            return app.config.get("LANGUAGE")

        return request.accept_languages.best_match(available_language_codes)


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
    import canaille.account
    import canaille.admin
    import canaille.groups
    import canaille.oidc

    app.url_map.strict_slashes = False

    app.register_blueprint(canaille.account.bp)
    app.register_blueprint(canaille.admin.bp)
    app.register_blueprint(canaille.groups.bp)
    app.register_blueprint(canaille.oidc.bp)


def create_app(config=None, validate=True):
    app = Flask(__name__)
    setup_config(app, config, validate)

    sentry_sdk = setup_sentry(app)
    try:
        setup_logging(app)
        init_backend(app)
        setup_oauth(app)
        setup_blueprints(app)
        setup_jinja(app)
        setup_i18n(app)
        setup_themer(app)

        @app.before_request
        def make_session_permanent():
            session.permanent = True
            app.permanent_session_lifetime = datetime.timedelta(days=365)

        @app.context_processor
        def global_processor():
            from .flaskutils import current_user

            return {
                "has_smtp": "SMTP" in app.config,
                "logo_url": app.config.get("LOGO"),
                "favicon_url": app.config.get("FAVICON", app.config.get("LOGO")),
                "website_name": app.config.get("NAME", "Canaille"),
                "user": current_user(),
                "menu": True,
                "locale": get_locale(),
            }

        @app.errorhandler(400)
        def bad_request(e):
            return render_template("error.html", error=400), 400

        @app.errorhandler(403)
        def unauthorized(e):
            return render_template("error.html", error=403), 403

        @app.errorhandler(404)
        def page_not_found(e):
            return render_template("error.html", error=404), 404

        @app.errorhandler(500)
        def server_error(e):  # pragma: no cover
            return render_template("error.html", error=500), 500

    except Exception as exc:  # pragma: no cover
        if sentry_sdk:
            sentry_sdk.capture_exception(exc)
        raise

    return app
