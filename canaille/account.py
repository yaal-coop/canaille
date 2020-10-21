from flask import Blueprint, request, flash, url_for, current_app
from flask import render_template, redirect
from flask_babel import gettext

from .forms import LoginForm, ProfileForm
from .flaskutils import current_user, user_needed
from .models import User


bp = Blueprint(__name__, "home")


@bp.route("/")
def index():
    if not current_user():
        return redirect(url_for("canaille.account.login"))
    return redirect(url_for("canaille.account.profile"))


@bp.route("/login", methods=("GET", "POST"))
def login():
    form = LoginForm(request.form or None)

    if request.form:
        if not form.validate() or not User.authenticate(
            form.login.data, form.password.data, True
        ):
            flash(gettext("Login failed, please check your information"), "error")
            return render_template("login.html", form=form)

        return redirect(url_for("canaille.account.index"))

    return render_template("login.html", form=form)


@bp.route("/logout")
def logout():
    if current_user():
        current_user().logout()
    return redirect("/")


@bp.route("/profile", methods=("GET", "POST"))
@user_needed()
def profile(user):
    claims = current_app.config["JWT"]["MAPPING"]
    data = {
        k.lower(): getattr(user, v)[0]
        if getattr(user, v) and isinstance(getattr(user, v), list)
        else getattr(user, v) or ""
        for k, v in claims.items()
    }
    form = ProfileForm(request.form or None, data=data)

    if request.form:
        if not form.validate():
            flash(gettext("Profile edition failed."), "error")

        else:
            for attribute in form:
                model_attribute_name = claims.get(attribute.name.upper())
                if not model_attribute_name or not hasattr(user, model_attribute_name):
                    continue

                user[model_attribute_name] = [attribute.data]

            if not form.password1.data or user.set_password(form.password1.data):
                flash(gettext("Profile updated successfuly."), "success")

            user.save()

    return render_template("profile.html", form=form, menuitem="profile")
