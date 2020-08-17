from flask import Blueprint, request, session
from flask import render_template, redirect, jsonify
from .models import User, Client
from .oauth2utils import require_oauth


bp = Blueprint(__name__, "home")


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

    clients = Client.filter()
    return render_template("home.html", clients=clients)


@bp.route("/logout")
def logout():
    del session["user_dn"]
    return redirect("/")


@bp.route("/api/me")
@require_oauth("profile")
def api_me():
    return jsonify(foo="bar")
