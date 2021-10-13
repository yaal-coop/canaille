import datetime
import ldap
import os
import toml

import canaille.admin
import canaille.admin.authorizations
import canaille.admin.clients
import canaille.admin.mail
import canaille.admin.tokens
import canaille.consents
import canaille.configuration
import canaille.oauth
import canaille.account
import canaille.groups
import canaille.well_known

from flask import Flask, g, request, render_template, session
from flask_babel import Babel

from .flaskutils import current_user
from .ldaputils import LDAPObject
from .oauth2utils import config_oauth
from .models import User, Token, AuthorizationCode, Client, Consent, Group

try:  # pragma: no cover
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    SENTRY = True
except Exception:
    SENTRY = False


def create_app(config=None):
    app = Flask(__name__)
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

    if not os.environ.get("FLASK_ENV") == "development":
        canaille.configuration.setup_dev_keypair(app.config)

    canaille.configuration.validate(app.config)
    setup_app(app)

    return app


def setup_ldap_tree(app):
    conn = ldap.initialize(app.config["LDAP"]["URI"])
    if app.config["LDAP"].get("TIMEOUT"):
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, app.config["LDAP"]["TIMEOUT"])
    conn.simple_bind_s(app.config["LDAP"]["BIND_DN"], app.config["LDAP"]["BIND_PW"])
    Token.initialize(conn)
    AuthorizationCode.initialize(conn)
    Client.initialize(conn)
    Consent.initialize(conn)
    conn.unbind_s()


def setup_ldap_connection(app):
    g.ldap = ldap.initialize(app.config["LDAP"]["URI"])
    g.ldap.simple_bind_s(app.config["LDAP"]["BIND_DN"], app.config["LDAP"]["BIND_PW"])


def teardown_ldap_connection(app):
    if "ldap" in g:
        g.ldap.unbind_s()


def setup_app(app):
    if SENTRY and app.config.get("SENTRY_DSN"):
        sentry_sdk.init(dsn=app.config["SENTRY_DSN"], integrations=[FlaskIntegration()])

    try:
        LDAPObject.root_dn = app.config["LDAP"]["ROOT_DN"]
        user_base = app.config["LDAP"]["USER_BASE"]
        if user_base.endswith(app.config["LDAP"]["ROOT_DN"]):
            user_base = user_base[: -len(app.config["LDAP"]["ROOT_DN"]) - 1]
        User.base = user_base
        group_base = app.config["LDAP"].get("GROUP_BASE")
        Group.base = group_base

        app.url_map.strict_slashes = False

        config_oauth(app)
        setup_ldap_tree(app)
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

        @app.before_request
        def before_request():
            setup_ldap_connection(app)

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
