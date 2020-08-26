import ldap
import os
import toml
from . import routes, clients, oauth, tokens, authorizations

from flask import Flask, g, request, render_template
from flask_babel import Babel

from .flaskutils import current_user
from .ldaputils import LDAPObjectHelper
from .oauth2utils import config_oauth


def create_app(config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        {
            "SESSION_COOKIE_NAME": "oidc-ldap-bridge",
            "OAUTH2_REFRESH_TOKEN_GENERATOR": True,
        }
    )
    if config:
        app.config.from_mapping(config)
    elif "CONFIG" in os.environ:
        app.config.from_mapping(toml.load(os.environ.get("CONFIG")))
    elif os.path.exists("config.toml"):
        app.config.from_mapping(toml.load("config.toml"))

    setup_app(app)
    return app


def setup_app(app):
    app.url_map.strict_slashes = False

    config_oauth(app)
    app.register_blueprint(routes.bp)
    app.register_blueprint(oauth.bp, url_prefix="/oauth")
    app.register_blueprint(clients.bp, url_prefix="/client")
    app.register_blueprint(tokens.bp, url_prefix="/token")
    app.register_blueprint(authorizations.bp, url_prefix="/authorization")

    babel = Babel(app)

    @app.before_request
    def before_request():
        LDAPObjectHelper.root_dn = app.config["LDAP"]["ROOT_DN"]
        g.ldap = ldap.initialize(app.config["LDAP"]["URI"])
        g.ldap.simple_bind_s(
            app.config["LDAP"]["BIND_DN"], app.config["LDAP"]["BIND_PW"]
        )

    @app.after_request
    def after_request(response):
        if "ldap" in g:
            g.ldap.unbind_s()
        return response

    @app.context_processor
    def global_processor():
        return {
            "logo_url": app.config.get("LOGO"),
            "website_name": app.config.get("NAME"),
            "user": current_user(),
            "menu": True,
        }

    @babel.localeselector
    def get_locale():
        user = getattr(g, "user", None)
        if user is not None:
            return user.locale

        if app.config.get("LANGUAGE"):
            return app.config.get("LANGUAGE")

        return request.accept_languages.best_match(["fr", "en"])

    @babel.timezoneselector
    def get_timezone():
        user = getattr(g, "user", None)
        if user is not None:
            return user.timezone

    @app.errorhandler(403)
    def unauthorized(e):
        return render_template("error.html", error=403), 403

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("error.html", error=404), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("error.html", error=500), 500
