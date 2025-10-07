from flask import Blueprint
from flask import abort
from flask import current_app
from flask import flash
from flask import g
from flask import redirect
from flask import request
from flask import session
from flask import url_for

from canaille.app import build_hash
from canaille.app.flask import smtp_needed
from canaille.app.i18n import gettext as _
from canaille.app.session import login_user
from canaille.app.session import logout_user
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.auth import auth_step
from canaille.core.auth import get_user_from_login
from canaille.core.auth import redirect_to_next_auth_step

from ...mails import send_password_initialization_mail
from ...mails import send_password_reset_mail
from ..forms import FirstLoginForm
from ..forms import ForgottenPasswordCodeForm
from ..forms import ForgottenPasswordForm
from ..forms import PasswordForm
from ..forms import PasswordResetForm

bp = Blueprint("password", __name__)


@bp.context_processor
def global_processor():
    return {
        "menu": False,
    }


@bp.route("/auth/password", methods=("GET", "POST"))
@auth_step("password")
def password():
    form = PasswordForm(request.form or None)
    form.render_field_macro_file = "core/partial/login_field.html"

    if not request.form or form.form_control():
        return render_template("core/auth/password.html", form=form)

    if g.auth.user and not g.auth.user.has_password() and current_app.features.has_smtp:
        return redirect(url_for("core.auth.password.firstlogin", user=g.auth.user))

    if not form.validate() or not g.auth.user:
        logout_user()
        flash(_("Login failed, please check your information"), "error")
        return render_template("core/auth/password.html", form=form)

    success, message = Backend.instance.check_user_password(
        g.auth.user, form.password.data
    )
    if not success:
        logout_user()
        current_app.logger.security(
            f"Failed password authentication for {g.auth.user_name}"
        )
        flash(message or _("Login failed, please check your information"), "error")
        return render_template("core/auth/password.html", form=form)

    current_app.logger.security(
        f"Successful password authentication for {g.auth.user_name}"
    )
    g.auth.set_step_finished("password")
    return redirect_to_next_auth_step()


@bp.route("/firstlogin/<user:user>", methods=("GET", "POST"))
def firstlogin(user):
    if user.has_password():
        abort(404)

    form = FirstLoginForm(request.form or None)
    if not request.form:
        return render_template("core/auth/firstlogin.html", form=form)

    form.validate()

    statuses = [
        send_password_initialization_mail(user, email) for email in (user.emails or [])
    ]
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

    return render_template("core/auth/firstlogin.html", form=form)


@bp.route("/reset", methods=["GET", "POST"])
@smtp_needed()
def forgotten():
    if not current_app.config["CANAILLE"]["ENABLE_PASSWORD_RECOVERY"]:
        abort(404)

    form = ForgottenPasswordForm(request.form)
    if not request.form:
        return render_template("core/auth/forgotten-password.html", form=form)

    item_name = "link" if current_app.features.has_trusted_hosts else "code"

    if not form.validate():
        flash(_(f"Could not send the password reset {item_name}."), "error")
        return render_template("core/auth/forgotten-password.html", form=form)

    user = get_user_from_login(form.login.data)
    success_message = _(
        f"A password reset {item_name} has been sent at your email address. "
        "You should receive it within a few minutes."
    )
    if current_app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] and (
        not user or not user.can_edit_self or user.locked
    ):
        flash(success_message, "success")
        return render_template("core/auth/forgotten-password.html", form=form)

    if not user.can_edit_self:
        flash(
            _(
                "The user '%(user)s' does not have permissions to update their password. "
                "We cannot send a password reset email.",
                user=user.formatted_name,
            ),
            "error",
        )
        return render_template("core/auth/forgotten-password.html", form=form)

    success = True
    for email in user.emails or []:
        if not send_password_reset_mail(user, email):
            success = False
        current_app.logger.security(
            f"Sending a reset password mail to {email} for {user.user_name}"
        )

    if success:
        flash(success_message, "success")
    else:
        flash(
            _("We encountered an issue while we sent the password recovery email."),
            "error",
        )

    if current_app.features.has_trusted_hosts:
        return render_template("core/auth/forgotten-password.html", form=form)
    else:
        return redirect(url_for(".forgotten_code", user=user))


@bp.route("/reset-code/<user:user>", methods=["GET", "POST"])
@smtp_needed()
def forgotten_code(user):
    if (
        not current_app.config["CANAILLE"]["ENABLE_PASSWORD_RECOVERY"]
        or current_app.features.has_trusted_hosts
    ):
        abort(404)

    if not user.can_edit_self:
        flash(
            _(
                "The user '%(user)s' does not have permissions to update their password. ",
                user=user.formatted_name,
            ),
            "error",
        )
        return redirect(url_for(".forgotten"))

    form = ForgottenPasswordCodeForm(request.form)
    if not request.form:
        return render_template("core/auth/forgotten-password-code.html", form=form)

    if not form.validate() or not user.is_email_or_sms_otp_valid(form.code.data):
        flash(_("Invalid code."), "error")
        return render_template("core/auth/forgotten-password-code.html", form=form)

    return redirect(url_for(".reset", user=user, token=form.code.data))


@bp.route("/reset/<user:user>/<token>", methods=["GET", "POST"])
def reset(user, token):
    if not current_app.config["CANAILLE"]["ENABLE_PASSWORD_RECOVERY"]:
        abort(404)
    form = PasswordResetForm(request.form)

    if current_app.features.has_trusted_hosts:
        token = build_hash(token)

    if not user or not user.is_email_or_sms_otp_valid(token):
        item_name = "link" if current_app.features.has_trusted_hosts else "code"
        flash(
            _(f"The password reset {item_name} that brought you here was invalid."),
            "error",
        )
        return redirect(url_for("core.account.index"))

    if not request.form or not form.validate():
        return render_template(
            "core/auth/reset-password.html", form=form, user=user, token=token
        )

    Backend.instance.set_user_password(user, form.password.data)
    user.clear_otp()
    Backend.instance.save(user)
    login_user(user)

    flash(_("Your password has been updated successfully"), "success")
    return redirect(
        session.pop(
            "redirect-after-login",
            url_for("core.account.profile_edition", edited_user=user),
        )
    )
