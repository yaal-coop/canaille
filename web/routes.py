from flask import Blueprint, request, session
from flask import render_template, redirect, jsonify
from authlib.oauth2 import OAuth2Error
from .models import User, Client
from .oauth2utils import authorization, require_oauth


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
