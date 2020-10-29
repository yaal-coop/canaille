import email.message
import hashlib
import smtplib

from flask import Blueprint, request, flash, url_for, current_app
from flask import render_template, redirect
from flask_babel import gettext as _

from .forms import LoginForm, ProfileForm, PasswordResetForm, ForgottenPasswordForm
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
            flash(_("Login failed, please check your information"), "error")
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
            flash(_("Profile edition failed."), "error")

        else:
            for attribute in form:
                model_attribute_name = claims.get(attribute.name.upper())
                if not model_attribute_name or not hasattr(user, model_attribute_name):
                    continue

                user[model_attribute_name] = [attribute.data]

            if not form.password1.data or user.set_password(form.password1.data):
                flash(_("Profile updated successfuly."), "success")

            user.save()

    return render_template("profile.html", form=form, menuitem="profile")


def profile_hash(user, password):
    return hashlib.sha256(
        current_app.config["SECRET_KEY"].encode("utf-8")
        + user.encode("utf-8")
        + password.encode("utf-8")
    ).hexdigest()


@bp.route("/reset", methods=["GET", "POST"])
def forgotten():
    form = ForgottenPasswordForm(request.form)
    if not request.form:
        return render_template("forgotten-password.html", form=form)

    if not form.validate():
        flash(_("Could not send the password reset link."), "error")
        return render_template("forgotten-password.html", form=form)

    user = User.get(form.login.data)

    if not user:
        flash(
            _("A password reset link has been sent at your email address."), "success"
        )
        return render_template("forgotten-password.html", form=form)

    recipient = user.mail
    base_url = current_app.config.get("URL") or request.url_root
    url = base_url + url_for(
        "canaille.account.reset",
        uid=user.uid[0],
        hash=profile_hash(user.uid[0], user.userPassword[0]),
    )[1:]
    subject = _("Password reset on {website_name}").format(
        website_name=current_app.config.get("NAME", url)
    )
    text_body = _(
        "To reset your password on {website_name}, visit the following link :\n{url}"
    ).format(website_name=current_app.config.get("NAME", url), url=url)

    msg = email.message.EmailMessage()
    msg.set_content(text_body)
    msg["Subject"] = subject
    msg["From"] = current_app.config["SMTP"]["FROM_ADDR"]
    msg["To"] = recipient

    success = True
    try:
        with smtplib.SMTP(
            host=current_app.config["SMTP"]["HOST"],
            port=current_app.config["SMTP"]["PORT"],
        ) as smtp:
            if current_app.config["SMTP"].get("TLS"):
                smtp.starttls()
            if current_app.config["SMTP"].get("LOGIN"):
                smtp.login(
                    user=current_app.config["SMTP"]["LOGIN"],
                    password=current_app.config["SMTP"].get("PASSWORD"),
                )
            smtp.send_message(msg)

    except smtplib.SMTPRecipientsRefused:
        pass

    except OSError:
        flash(_("Could not reset your password"), "error")
        success = False

    if success:
        flash(
            _("A password reset link has been sent at your email address."), "success"
        )

    return render_template("forgotten-password.html", form=form)


@bp.route("/reset/<uid>/<hash>", methods=["GET", "POST"])
def reset(uid, hash):
    form = PasswordResetForm(request.form)
    user = User.get(uid)

    if not user or hash != profile_hash(user.uid[0], user.userPassword[0]):
        flash(
            _("The password reset link that brought you here was invalid."),
            "error",
        )
        return redirect(url_for("canaille.account.index"))

    if request.form and form.validate():
        user.set_password(form.password.data)
        user.login()

        flash(_("Your password has been updated successfuly"), "success")
        return redirect(url_for("canaille.account.profile", user_id=uid))

    return render_template("reset-password.html", form=form, uid=uid, hash=hash)
