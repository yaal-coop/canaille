from canaille.app import build_hash
from canaille.app import models
from canaille.app.flask import current_user
from canaille.app.flask import login_user
from canaille.app.flask import logout_user
from canaille.app.flask import smtp_needed
from canaille.app.i18n import gettext as _
from canaille.app.themes import render_template
from canaille.backends import BaseBackend
from flask import abort
from flask import Blueprint
from flask import current_app
from flask import flash
from flask import redirect
from flask import request
from flask import session
from flask import url_for

from ..mails import send_password_initialization_mail
from ..mails import send_password_reset_mail
from .forms import FirstLoginForm
from .forms import ForgottenPasswordForm
from .forms import LoginForm
from .forms import PasswordForm
from .forms import PasswordResetForm

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=("GET", "POST"))
def login():
    if current_user():
        return redirect(
            url_for("core.account.profile_edition", edited_user=current_user())
        )

    form = LoginForm(request.form or None)
    form.render_field_macro_file = "partial/login_field.html"
    form["login"].render_kw["placeholder"] = BaseBackend.get().login_placeholder()

    if not request.form or form.form_control():
        return render_template("login.html", form=form)

    user = models.User.get_from_login(form.login.data)
    if user and not user.has_password():
        return redirect(url_for("core.auth.firstlogin", user=user))

    if not form.validate():
        logout_user()
        flash(_("Login failed, please check your information"), "error")
        return render_template("login.html", form=form)

    session["attempt_login"] = form.login.data
    return redirect(url_for("core.auth.password"))


@bp.route("/password", methods=("GET", "POST"))
def password():
    if "attempt_login" not in session:
        return redirect(url_for("core.auth.login"))

    form = PasswordForm(request.form or None)
    form.render_field_macro_file = "partial/login_field.html"

    if not request.form or form.form_control():
        return render_template(
            "password.html", form=form, username=session["attempt_login"]
        )

    user = models.User.get_from_login(session["attempt_login"])
    if user and not user.has_password():
        return redirect(url_for("core.auth.firstlogin", user=user))

    if not form.validate() or not user:
        logout_user()
        flash(_("Login failed, please check your information"), "error")
        return render_template(
            "password.html", form=form, username=session["attempt_login"]
        )

    success, message = user.check_password(form.password.data)
    if not success:
        logout_user()
        flash(message or _("Login failed, please check your information"), "error")
        return render_template(
            "password.html", form=form, username=session["attempt_login"]
        )

    del session["attempt_login"]
    login_user(user)
    flash(
        _("Connection successful. Welcome %(user)s", user=user.formatted_name),
        "success",
    )
    return redirect(session.pop("redirect-after-login", url_for("core.account.index")))


@bp.route("/logout")
def logout():
    user = current_user()

    if user:
        flash(
            _(
                "You have been disconnected. See you next time %(user)s",
                user=user.formatted_name,
            ),
            "success",
        )
        logout_user()
    return redirect("/")


@bp.route("/firstlogin/<user:user>", methods=("GET", "POST"))
def firstlogin(user):
    if user.has_password():
        abort(404)

    form = FirstLoginForm(request.form or None)
    if not request.form:
        return render_template("firstlogin.html", form=form, user=user)

    form.validate()

    statuses = [send_password_initialization_mail(user, email) for email in user.emails]
    success = all(statuses)
    if success:
        flash(
            _(
                "A password initialization link has been sent at your email address. "
                "You should receive it within a few minutes."
            ),
            "success",
        )
    else:
        flash(_("Could not send the password initialization email"), "error")

    return render_template("firstlogin.html", form=form)


@bp.route("/reset", methods=["GET", "POST"])
@smtp_needed()
def forgotten():
    if not current_app.config.get("ENABLE_PASSWORD_RECOVERY", True):
        abort(404)

    form = ForgottenPasswordForm(request.form)
    if not request.form:
        return render_template("forgotten-password.html", form=form)

    if not form.validate():
        flash(_("Could not send the password reset link."), "error")
        return render_template("forgotten-password.html", form=form)

    user = models.User.get_from_login(form.login.data)
    success_message = _(
        "A password reset link has been sent at your email address. "
        "You should receive it within a few minutes."
    )
    if current_app.config.get("HIDE_INVALID_LOGINS", True) and (
        not user or not user.can_edit_self
    ):
        flash(success_message, "success")
        return render_template("forgotten-password.html", form=form)

    if not user.can_edit_self:
        flash(
            _(
                "The user '%(user)s' does not have permissions to update their password. "
                "We cannot send a password reset email.",
                user=user.formatted_name,
            ),
            "error",
        )
        return render_template("forgotten-password.html", form=form)

    statuses = [send_password_reset_mail(user, email) for email in user.emails]
    success = all(statuses)

    if success:
        flash(success_message, "success")
    else:
        flash(
            _("We encountered an issue while we sent the password recovery email."),
            "error",
        )

    return render_template("forgotten-password.html", form=form)


@bp.route("/reset/<user:user>/<hash>", methods=["GET", "POST"])
def reset(user, hash):
    if not current_app.config.get("ENABLE_PASSWORD_RECOVERY", True):
        abort(404)

    form = PasswordResetForm(request.form)
    hashes = {
        build_hash(
            user.identifier,
            email,
            user.password if user.has_password() else "",
        )
        for email in user.emails
    }
    if not user or hash not in hashes:
        flash(
            _("The password reset link that brought you here was invalid."),
            "error",
        )
        return redirect(url_for("core.account.index"))

    if request.form and form.validate():
        user.set_password(form.password.data)
        login_user(user)

        flash(_("Your password has been updated successfully"), "success")
        return redirect(
            session.pop(
                "redirect-after-login",
                url_for("core.account.profile_edition", edited_user=user),
            )
        )

    return render_template("reset-password.html", form=form, user=user, hash=hash)
