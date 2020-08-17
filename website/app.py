import ldap
import os
import toml

from flask import Flask, g, request
from flask_babel import Babel

from .oauth2 import config_oauth
from .routes import bp


def create_app(config=None):
    app = Flask(__name__)

    config = toml.load(os.environ.get("CONFIG", "config.toml"))
    app.config.from_mapping(config)

    app.url_map.strict_slashes = False

    setup_app(app)
    return app


def setup_app(app):
    @app.before_request
    def before_request():
        g.ldap = ldap.initialize(app.config["LDAP"]["URI"])
        g.ldap.simple_bind_s(app.config["LDAP"]["BIND_USER"], app.config["LDAP"]["BIND_PW"])

    @app.after_request
    def after_request(response):
        if "ldap" in g:
            g.ldap.unbind_s()
        return response

    config_oauth(app)
    app.register_blueprint(bp, url_prefix="")

    babel = Babel(app)

    @app.context_processor
    def global_processor():
        return {
            "logo_url": app.config.get("LOGO"),
            "website_name": app.config.get("NAME"),
        }

    @babel.localeselector
    def get_locale():
        user = getattr(g, 'user', None)
        if user is not None:
            return user.locale

        if app.config.get("LANGUAGE"):
            return app.config.get("LANGUAGE")

        return request.accept_languages.best_match(['fr', 'en'])

    @babel.timezoneselector
    def get_timezone():
        user = getattr(g, 'user', None)
        if user is not None:
            return user.timezone
