from authlib.integrations.flask_client import OAuth
from authlib.oidc.discovery import get_well_known_url
from flask import flash
from flask import Flask
from flask import redirect
from flask import render_template
from flask import session
from flask import url_for


def create_app():
    app = Flask(__name__)
    app.config.from_envvar("CONFIG")
    app.static_folder = "../../canaille/static"

    oauth = OAuth()
    oauth.init_app(app)
    oauth.register(
        name="canaille",
        client_id=app.config["OAUTH_CLIENT_ID"],
        client_secret=app.config["OAUTH_CLIENT_SECRET"],
        server_metadata_url=get_well_known_url(
            app.config["OAUTH_AUTH_SERVER"], external=True
        ),
        client_kwargs={"scope": "openid profile email groups"},
    )

    @app.route("/")
    def index():
        return render_template(
            "index.html", user=session.get("user"), name=app.config["NAME"]
        )

    @app.route("/login")
    def login():
        return oauth.canaille.authorize_redirect(url_for("authorize", _external=True))

    @app.route("/authorize")
    def authorize():
        token = oauth.canaille.authorize_access_token()
        session["user"] = token.get("userinfo")
        flash("You have been successfully logged in.", "success")
        return redirect(url_for("index"))

    @app.route("/logout")
    def logout():
        try:
            del session["user"]
        except KeyError:
            pass

        flash("You have been successfully logged out.", "success")
        return redirect(url_for("index"))

    return app
