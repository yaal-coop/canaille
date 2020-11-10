from authlib.integrations.flask_client import OAuth
from authlib.oidc.discovery import get_well_known_url
from flask import Flask, render_template, redirect, url_for, flash, session


def create_app():
    app = Flask(__name__)
    app.config.from_envvar("CONFIG")
    app.static_folder = "../../canaille/static"

    oauth = OAuth()
    oauth.init_app(app)
    oauth.register(
        name="yaal",
        client_id=app.config["OAUTH_CLIENT_ID"],
        client_secret=app.config["OAUTH_CLIENT_SECRET"],
        server_metadata_url=get_well_known_url(
            app.config["OAUTH_AUTH_SERVER"], external=True
        ),
        client_kwargs={"scope": "openid profile email"},
    )

    @app.route("/")
    def index():
        return render_template(
            "index.html", user=session.get("user"), name=app.config["NAME"]
        )

    @app.route("/login")
    def login():
        return oauth.yaal.authorize_redirect(url_for("authorize", _external=True))

    @app.route("/authorize")
    def authorize():
        token = oauth.yaal.authorize_access_token()
        userinfo = oauth.yaal.parse_id_token(token)
        session["user"] = userinfo
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
