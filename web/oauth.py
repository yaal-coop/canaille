import wtforms
from authlib.oauth2 import OAuth2Error
from flask import Blueprint, request, session, redirect
from flask import render_template, jsonify, flash
from flask_babel import gettext
from flask_wtf import FlaskForm
from .models import User, Client
from .oauth2utils import authorization


bp = Blueprint(__name__, "oauth")


class LoginForm(FlaskForm):
    login = wtforms.StringField(
        gettext("Username"),
        validators=[wtforms.validators.DataRequired()],
        render_kw={"placeholder": "mdupont"},
    )
    password = wtforms.PasswordField(
        gettext("Password"), validators=[wtforms.validators.DataRequired()]
    )


@bp.route("/authorize", methods=["GET", "POST"])
def authorize():
    user = User.get(session["user_dn"]) if "user_dn" in session else None
    client = Client.get(request.values["client_id"])

    if not user:
        form = LoginForm(request.form or None)
        if request.method == "GET":
            return render_template("login.html", form=form)

        if not form.validate():
            flash(gettext("Login failed, please check your information"), "error")
            return render_template("login.html", form=form)

        user = User.get(form.login.data)
        if not user or not user.check_password(form.password.data):
            flash(gettext("Login failed, please check your information"), "error")
            return render_template("login.html", form=form)

        session["user_dn"] = form.login.data
        return redirect(request.url)

    if request.method == "GET":
        try:
            grant = authorization.validate_consent_request(end_user=user)
        except OAuth2Error as error:
            return jsonify(dict(error.get_body()))

        return render_template("authorize.html", user=user, grant=grant, client=client)

    if request.form["answer"] == "logout":
        del session["user_dn"]
        flash(gettext("You have been successfully logged out."), "success")
        return redirect(request.url)

    if request.form["answer"] == "deny":
        grant_user = None

    if request.form["answer"] == "accept":
        grant_user = user.dn

    return authorization.create_authorization_response(grant_user=grant_user)


@bp.route("/token", methods=["POST"])
def issue_token():
    return authorization.create_token_response()
