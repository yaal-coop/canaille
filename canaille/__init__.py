import ldap
import os
import toml

import canaille.admin
import canaille.admin.authorizations
import canaille.admin.clients
import canaille.admin.mail
import canaille.admin.tokens
import canaille.consents
import canaille.commands
import canaille.oauth
import canaille.account
import canaille.well_known

from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend

from flask import Flask, g, request, render_template
from flask_babel import Babel

from .flaskutils import current_user
from .ldaputils import LDAPObject
from .oauth2utils import config_oauth
from .models import User, Token, AuthorizationCode, Client, Consent

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

    setup_dev_keypair(app)

    if not os.path.exists(app.config["JWT"]["PUBLIC_KEY"]) or not os.path.exists(
        app.config["JWT"]["PRIVATE_KEY"]
    ):
        raise Exception("Invalid keypair")
    setup_app(app)

    return app


def setup_dev_keypair(app):
    if not os.environ.get("FLASK_ENV") == "development":
        return

    if os.path.exists(app.config["JWT"]["PUBLIC_KEY"]) or os.path.exists(
        app.config["JWT"]["PRIVATE_KEY"]
    ):
        return

    key = rsa.generate_private_key(
        backend=crypto_default_backend(), public_exponent=65537, key_size=2048
    )
    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption(),
    )
    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH, crypto_serialization.PublicFormat.OpenSSH
    )

    with open(app.config["JWT"]["PUBLIC_KEY"], "wb") as fd:
        fd.write(public_key)

    with open(app.config["JWT"]["PRIVATE_KEY"], "wb") as fd:
        fd.write(private_key)


def setup_ldap_tree(app):
    conn = ldap.initialize(app.config["LDAP"]["URI"])
    conn.simple_bind_s(app.config["LDAP"]["BIND_DN"], app.config["LDAP"]["BIND_PW"])
    Token.initialize(conn)
    AuthorizationCode.initialize(conn)
    Client.initialize(conn)
    Consent.initialize(conn)
    conn.unbind_s()


def setup_ldap(app):
    g.ldap = ldap.initialize(app.config["LDAP"]["URI"])
    g.ldap.simple_bind_s(app.config["LDAP"]["BIND_DN"], app.config["LDAP"]["BIND_PW"])


def teardown_ldap(app):
    if "ldap" in g:
        g.ldap.unbind_s()


def setup_app(app):
    if SENTRY and app.config.get("SENTRY_DSN"):
        sentry_sdk.init(dsn=app.config["SENTRY_DSN"], integrations=[FlaskIntegration()])

    try:
        LDAPObject.root_dn = app.config["LDAP"]["ROOT_DN"]
        base = app.config["LDAP"]["USER_BASE"]
        if base.endswith(app.config["LDAP"]["ROOT_DN"]):
            base = base[: -len(app.config["LDAP"]["ROOT_DN"]) - 1]
        User.base = base

        app.url_map.strict_slashes = False

        config_oauth(app)
        setup_ldap_tree(app)
        app.register_blueprint(canaille.account.bp)
        app.register_blueprint(canaille.oauth.bp, url_prefix="/oauth")
        app.register_blueprint(canaille.commands.bp)
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
            setup_ldap(app)

        @app.after_request
        def after_request(response):
            teardown_ldap(app)
            return response

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
