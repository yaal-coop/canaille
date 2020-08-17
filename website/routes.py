import datetime
from flask import Blueprint, request, session
from flask import render_template, redirect, jsonify
from werkzeug.security import gen_salt
from authlib.oauth2 import OAuth2Error
from .models import User, Client
from .oauth2 import authorization, require_oauth


bp = Blueprint(__name__, "home")


def current_user():
    if "user_dn" in session:
        return User.get(session["user_dn"])
    return None


@bp.route("/", methods=("GET", "POST"))
def home():
    if request.method == "POST":
        username = request.form.get("username")
        user = User.get(username)

        if not user:
            user = User(cn=username, sn=username)
            user.save()

        session["user_dn"] = user.dn
        return redirect("/")

    user = current_user()
    if user:
        clients = Client.filter()
    else:
        clients = []

    return render_template("home.html", user=user, clients=clients)


def split_by_crlf(s):
    return [v for v in s.splitlines() if v]


@bp.route("/create_client", methods=("GET", "POST"))
def create_client():
    user = current_user()
    if not user:
        return redirect("/")

    if request.method == "GET":
        return render_template("create_client.html")

    form = request.form
    client_id = gen_salt(24)
    client_id_issued_at = datetime.datetime.now().strftime("%Y%m%d%H%M%SZ")
    client = Client(
        oauthClientID=client_id,
        oauthIssueDate=client_id_issued_at,
        oauthClientName=form["client_name"],
        oauthClientURI=form["client_uri"],
        oauthGrantType=split_by_crlf(form["grant_type"]),
        oauthRedirectURI=split_by_crlf(form["redirect_uri"]),
        oauthResponseType=split_by_crlf(form["response_type"]),
        oauthScope=form["scope"],
        oauthTokenEndpointAuthMethod=form["token_endpoint_auth_method"],
        oauthClientSecret=""
        if form["token_endpoint_auth_method"] == "none"
        else gen_salt(48),
    )
    client.save()
    return redirect("/")


@bp.route("/oauth/authorize", methods=["GET", "POST"])
def authorize():
    user = current_user()
    if request.method == "GET":
        try:
            grant = authorization.validate_consent_request(end_user=user)
        except OAuth2Error as error:
            return jsonify(dict(error.get_body()))
        return render_template("authorize.html", user=user, grant=grant)

    if not user and "username" in request.form:
        username = request.form.get("username")
        user = User.get(username)

    if request.form["confirm"]:
        grant_user = user
    else:
        grant_user = None

    return authorization.create_authorization_response(grant_user=grant_user)


@bp.route("/logout")
def logout():
    del session["user_dn"]
    return redirect("/")


@bp.route("/oauth/token", methods=["POST"])
def issue_token():
    return authorization.create_token_response()


@bp.route("/api/me")
@require_oauth("profile")
def api_me():
    return jsonify(foo="bar")
