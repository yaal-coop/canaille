from flask import Blueprint, request, flash, url_for
from flask import render_template, redirect, jsonify
from flask_babel import gettext

from .forms import LoginForm
from .flaskutils import current_user
from .models import User
from .oauth2utils import require_oauth


bp = Blueprint(__name__, "home")


@bp.route("/")
def index():
    if not current_user():
        return redirect(url_for("web.routes.login"))
    return redirect(url_for("web.tokens.tokens"))


@bp.route("/login", methods=("GET", "POST"))
def login():
    form = LoginForm(request.form or None)

    if request.form:
        if not form.validate() or not User.authenticate(
            form.login.data, form.password.data, True
        ):
            flash(gettext("Login failed, please check your information"), "error")
            return render_template("login.html", form=form)

        return redirect(url_for("web.routes.index"))

    return render_template("login.html", form=form)


@bp.route("/logout")
def logout():
    if current_user():
        current_user().logout()
    return redirect("/")


@bp.route("/api/me")
@require_oauth("profile")
def api_me():
    return jsonify(foo="bar")
