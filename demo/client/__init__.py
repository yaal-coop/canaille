from urllib.parse import urlsplit
from urllib.parse import urlunsplit

from authlib.integrations.flask_client import OAuth
from authlib.oidc.discovery import get_well_known_url
from flask import current_app
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
        session["id_token"] = token["id_token"]
        flash("You have been successfully logged in.", "success")
        return redirect(url_for("index"))

    @app.route("/logout")
    def logout():
        try:
            del session["user"]
        except KeyError:
            pass

        flash("You have been successfully logged out", "success")

        oauth.canaille.load_server_metadata()
        end_session_endpoint = oauth.canaille.server_metadata.get(
            "end_session_endpoint"
        )
        end_session_url = set_parameter_in_url_query(
            end_session_endpoint,
            client_id=current_app.config["OAUTH_CLIENT_ID"],
            id_token_hint=session["id_token"],
            post_logout_redirect_uri=url_for("index", _external=True),
        )
        return redirect(end_session_url)

    return app


def set_parameter_in_url_query(url, **kwargs):
    split = list(urlsplit(url))

    parameters = "&".join(f"{key}={value}" for key, value in kwargs.items())

    if split[3]:
        split[3] = f"{split[3]}&{parameters}"
    else:
        split[3] = parameters

    return urlunsplit(split)
