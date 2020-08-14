import ldap
import os
from flask import Flask, g
#from .models import db
from .oauth2 import config_oauth
from .routes import bp


def create_app(config=None):
    app = Flask(__name__)

    # load default configuration
    app.config.from_object("website.settings")

    # load environment configuration
    if "WEBSITE_CONF" in os.environ:
        app.config.from_envvar("WEBSITE_CONF")

    # load app specified configuration
    if config is not None:
        if isinstance(config, dict):
            app.config.update(config)
        elif config.endswith(".py"):
            app.config.from_pyfile(config)

    setup_app(app)
    return app


def setup_app(app):
    @app.before_request
    def before_request():
        g.ldap = ldap.initialize("ldap://ldap")
        g.ldap.simple_bind_s("cn=admin,dc=mydomain,dc=tld", "admin")

    @app.after_request
    def after_request(response):
        if "ldap" in g:
            g.ldap.unbind_s()
        return response

#    # Create tables if they do not exist already
#    @app.before_first_request
#    def create_tables():
#        db.create_all()
#
#    db.init_app(app)
    config_oauth(app)
    app.register_blueprint(bp, url_prefix="")
