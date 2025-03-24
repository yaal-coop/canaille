from authlib.common.errors import AuthlibBaseError
from authlib.common.urls import add_params_to_uri
from authlib.integrations.flask_client import OAuth
from authlib.oidc.discovery import get_well_known_url
from flask import Flask
from flask import current_app
from flask import flash
from flask import redirect
from flask import render_template
from flask import session
from flask import url_for

oauth = OAuth()


def setup_routes(app):
    @app.route("/")
    @app.route("/tos")
    @app.route("/policy")
    def index():
        return render_template(
            "index.html", user=session.get("user"), name=app.config["NAME"]
        )

    @app.route("/register")
    def register():
        return oauth.canaille.authorize_redirect(
            url_for("register_callback", _external=True), prompt="create"
        )

    @app.route("/register_callback")
    def register_callback():
        try:
            token = oauth.canaille.authorize_access_token()
            session["user"] = token.get("userinfo")
            session["id_token"] = token["id_token"]
            flash("You account has been successfully created.", "success")
        except AuthlibBaseError as exc:
            flash(f"An error happened during registration: {exc.description}", "error")

        return redirect(url_for("index"))

    @app.route("/login")
    def login():
        return oauth.canaille.authorize_redirect(
            url_for("login_callback", _external=True)
        )

    @app.route("/login_callback")
    def login_callback():
        try:
            token = oauth.canaille.authorize_access_token()
            session["user"] = token.get("userinfo")
            session["id_token"] = token["id_token"]
            flash("You have been successfully logged in.", "success")
        except AuthlibBaseError as exc:
            flash(f"An error happened during login: {exc.description}", "error")

        return redirect(url_for("index"))

    @app.route("/logout")
    def logout():
        oauth.canaille.load_server_metadata()
        end_session_endpoint = oauth.canaille.server_metadata.get(
            "end_session_endpoint"
        )
        end_session_url = add_params_to_uri(
            end_session_endpoint,
            dict(
                client_id=current_app.config["OAUTH_CLIENT_ID"],
                id_token_hint=session["id_token"],
                post_logout_redirect_uri=url_for("logout_callback", _external=True),
            ),
        )
        return redirect(end_session_url)

    @app.route("/logout_callback")
    def logout_callback():
        try:
            del session["user"]
        except KeyError:
            pass

        flash("You have been successfully logged out", "success")
        return redirect(url_for("index"))


def setup_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name="canaille",
        client_id=app.config["OAUTH_CLIENT_ID"],
        client_secret=app.config["OAUTH_CLIENT_SECRET"],
        server_metadata_url=get_well_known_url(
            app.config["OAUTH_AUTH_SERVER"], external=True
        ),
        client_kwargs={"scope": "openid profile email phone address groups"},
    )


def create_app():
    app = Flask(__name__)
    app.config.from_envvar("CONFIG")
    app.static_folder = "../../canaille/static"

    setup_routes(app)
    setup_oauth(app)
    return app
