import datetime
import ldap
import logging
import os
import toml

import canaille.account
import canaille.admin
import canaille.admin.authorizations
import canaille.admin.clients
import canaille.admin.mail
import canaille.admin.tokens
import canaille.consents
import canaille.configuration
import canaille.installation
import canaille.oauth
import canaille.groups
import canaille.well_known

from flask import Flask, g, request, session
from flask_babel import Babel, gettext as _
from flask_themer import Themer, render_template, FileSystemThemeLoader
from logging.config import dictConfig

from .flaskutils import current_user, base64picture
from .ldaputils import LDAPObject
from .oauth2utils import setup_oauth
from .models import User, Group

try:  # pragma: no cover
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    SENTRY = True
except Exception:
    SENTRY = False


def setup_config(app, config=None, validate=True):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    app.config.from_mapping(
        {
            "SESSION_COOKIE_NAME": "canaille",
            "OAUTH2_REFRESH_TOKEN_GENERATOR": True,
        }
    )
    if config:
        app.config.from_mapping(config)
    elif "CONFIG" in os.environ:
        app.config.from_mapping(toml.load(os.environ.get("CONFIG")))
    elif os.path.exists(os.path.join(dir_path, "conf", "config.toml")):
        app.config.from_mapping(
            toml.load(os.path.join(dir_path, "conf", "config.toml"))
        )
    else:
        raise Exception(
            "No configuration file found. "
            "Either create conf/config.toml or set the 'CONFIG' variable environment."
        )

    if os.environ.get("FLASK_ENV") == "development":
        canaille.installation.setup_keypair(app.config)

    if validate:
        canaille.configuration.validate(app.config)


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
        }
    )


def setup_ldap_models(app):
    LDAPObject.root_dn = app.config["LDAP"]["ROOT_DN"]

    user_base = app.config["LDAP"]["USER_BASE"]
    if user_base.endswith(app.config["LDAP"]["ROOT_DN"]):
        user_base = user_base[: -len(app.config["LDAP"]["ROOT_DN"]) - 1]
    User.base = user_base
    User.id = app.config["LDAP"].get("USER_ID_ATTRIBUTE", "cn")

    group_base = app.config["LDAP"].get("GROUP_BASE")
    if group_base.endswith(app.config["LDAP"]["ROOT_DN"]):
        group_base = group_base[: -len(app.config["LDAP"]["ROOT_DN"]) - 1]
    Group.base = group_base
    Group.id = app.config["LDAP"].get("GROUP_ID_ATTRIBTUE", "cn")


def setup_ldap_connection(app):
    try:  # pragma: no-cover
        if request.endpoint == "static":
            return
    except RuntimeError:
        pass

    try:
        g.ldap = ldap.initialize(app.config["LDAP"]["URI"])
        if app.config["LDAP"].get("TIMEOUT"):
            g.ldap.set_option(ldap.OPT_NETWORK_TIMEOUT, app.config["LDAP"]["TIMEOUT"])
        g.ldap.simple_bind_s(
            app.config["LDAP"]["BIND_DN"], app.config["LDAP"]["BIND_PW"]
        )

    except ldap.SERVER_DOWN:
        message = _("Could not connect to the LDAP server '{uri}'").format(
            uri=app.config["LDAP"]["URI"]
        )
        logging.error(message)
        return (
            render_template(
                "error.html",
                error=500,
                icon="database",
                debug=app.config.get("DEBUG", False),
                description=message,
            ),
            500,
        )

    except ldap.INVALID_CREDENTIALS:
        message = _("LDAP authentication failed with user '{user}'").format(
            user=app.config["LDAP"]["BIND_DN"]
        )
        logging.error(message)
        return (
            render_template(
                "error.html",
                error=500,
                icon="key",
                debug=app.config.get("DEBUG", False),
                description=message,
            ),
            500,
        )


def teardown_ldap_connection(app):
    if "ldap" in g:
        g.ldap.unbind_s()


def setup_jinja(app):
    app.jinja_env.filters["base64picture"] = base64picture


def setup_babel(app):
    babel = Babel(app)

    @babel.localeselector
    def get_locale():
        user = getattr(g, "user", None)
        if user is not None:
            return user.locale

        if app.config.get("LANGUAGE"):
            return app.config.get("LANGUAGE")

        return request.accept_languages.best_match(["fr_FR", "en_US"])

    @babel.timezoneselector
    def get_timezone():
        user = getattr(g, "user", None)
        if user is not None:
            return user.timezone


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
    app.url_map.strict_slashes = False

    app.register_blueprint(canaille.account.bp)
    app.register_blueprint(canaille.groups.bp, url_prefix="/groups")
    app.register_blueprint(canaille.oauth.bp, url_prefix="/oauth")
    app.register_blueprint(canaille.consents.bp, url_prefix="/consent")
    app.register_blueprint(canaille.well_known.bp, url_prefix="/.well-known")
    app.register_blueprint(canaille.admin.tokens.bp, url_prefix="/admin/token")
    app.register_blueprint(
        canaille.admin.authorizations.bp, url_prefix="/admin/authorization"
    )
    app.register_blueprint(canaille.admin.clients.bp, url_prefix="/admin/client")
    app.register_blueprint(canaille.admin.mail.bp, url_prefix="/admin/mail")


def create_app(config=None, validate=True):
    app = Flask(__name__)
    setup_config(app, config, validate)

    if SENTRY and app.config.get("SENTRY_DSN"):
        sentry_sdk.init(dsn=app.config["SENTRY_DSN"], integrations=[FlaskIntegration()])

    try:
        setup_logging(app)
        setup_ldap_models(app)
        setup_oauth(app)
        setup_blueprints(app)
        setup_jinja(app)
        setup_babel(app)
        setup_themer(app)

        @app.before_request
        def before_request():
            return setup_ldap_connection(app)

        @app.after_request
        def after_request(response):
            teardown_ldap_connection(app)
            return response

        @app.before_request
        def make_session_permanent():
            session.permanent = True
            app.permanent_session_lifetime = datetime.timedelta(days=365)

        @app.context_processor
        def global_processor():
            return {
                "has_smtp": "SMTP" in app.config,
                "logo_url": app.config.get("LOGO"),
                "favicon_url": app.config.get("FAVICON", app.config.get("LOGO")),
                "website_name": app.config.get("NAME"),
                "user": current_user(),
                "menu": True,
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
        def server_error(e):
            return render_template("error.html", error=500), 500

    except Exception as exc:
        if SENTRY and app.config.get("SENTRY_DSN"):
            sentry_sdk.capture_exception(exc)
        raise

    return app
