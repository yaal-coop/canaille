import datetime

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    request,
    session,
    url_for,
)

from canaille.app import build_hash, get_b64encoded_qr_image
from canaille.app.flask import current_user, login_user, logout_user, smtp_needed
from canaille.app.i18n import gettext as _
from canaille.app.session import current_user, login_user, logout_user
from canaille.app.themes import render_template
from canaille.backends import Backend
from canaille.core.endpoints.forms import TwoFactorForm

from ..mails import send_password_initialization_mail, send_password_reset_mail
from .forms import (
    FirstLoginForm,
    ForgottenPasswordForm,
    LoginForm,
    PasswordForm,
    PasswordResetForm,
)

bp = Blueprint("auth", __name__)


@bp.context_processor
def global_processor():
    return {
        "menu": False,
    }


@bp.route("/login", methods=("GET", "POST"))
def login():
    if current_user():
        return redirect(
            url_for("core.account.profile_edition", edited_user=current_user())
        )

    form = LoginForm(request.form or None)
    form.render_field_macro_file = "partial/login_field.html"
    form["login"].render_kw["placeholder"] = Backend.instance.login_placeholder()

    if not request.form or form.form_control():
        return render_template("login.html", form=form)

    user = Backend.instance.get_user_from_login(form.login.data)
    if user and not user.has_password() and current_app.features.has_smtp:
        return redirect(url_for("core.auth.firstlogin", user=user))

    if not form.validate():
        logout_user()
        flash(_("Login failed, please check your information"), "error")
        return render_template("login.html", form=form)

    session["attempt_login"] = form.login.data
    return redirect(url_for("core.auth.password"))


@bp.route("/password", methods=("GET", "POST"))
def password():
    if current_user():
        return redirect(
            url_for("core.account.profile_edition", edited_user=current_user())
        )

    if "attempt_login" not in session:
        flash(_("Cannot remember the login you attempted to sign in with"), "warning")
        return redirect(url_for("core.auth.login"))

    form = PasswordForm(request.form or None)
    form.render_field_macro_file = "partial/login_field.html"

    if not request.form or form.form_control():
        return render_template(
            "password.html", form=form, username=session["attempt_login"]
        )

    user = Backend.instance.get_user_from_login(session["attempt_login"])
    if user and not user.has_password() and current_app.features.has_smtp:
        return redirect(url_for("core.auth.firstlogin", user=user))

    if not form.validate() or not user:
        logout_user()
        flash(_("Login failed, please check your information"), "error")
        return render_template(
            "password.html", form=form, username=session["attempt_login"]
        )

    success, message = Backend.instance.check_user_password(user, form.password.data)
    request_ip = request.remote_addr or "unknown IP"
    if not success:
        logout_user()
        current_app.logger.security(
            f'Failed login attempt for {session["attempt_login"]} from {request_ip}'
        )
        flash(message or _("Login failed, please check your information"), "error")
        return render_template(
            "password.html", form=form, username=session["attempt_login"]
        )

    if not current_app.features.has_otp:
        current_app.logger.security(
            f'Succeed login attempt for {session["attempt_login"]} from {request_ip}'
        )
        del session["attempt_login"]
        login_user(user)
        flash(
            _("Connection successful. Welcome %(user)s", user=user.formatted_name),
            "success",
        )
        return redirect(
            session.pop("redirect-after-login", url_for("core.account.index"))
        )
    else:
        session["attempt_login_with_correct_password"] = session.pop("attempt_login")
        if not user.last_otp_login:
            flash(
                "You have not enabled Two-Factor Authentication. Please enable it first to login.",
                "info",
            )
            return redirect(url_for("core.auth.setup_two_factor_auth"))
        return redirect(url_for("core.auth.verify_two_factor_auth"))


@bp.route("/logout")
def logout():
    user = current_user()

    if user:
        request_ip = request.remote_addr or "unknown IP"
        current_app.logger.security(f"Logout {user.identifier} from {request_ip}")

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
    if not current_app.config["CANAILLE"]["ENABLE_PASSWORD_RECOVERY"]:
        abort(404)

    form = ForgottenPasswordForm(request.form)
    if not request.form:
        return render_template("forgotten-password.html", form=form)

    if not form.validate():
        flash(_("Could not send the password reset link."), "error")
        return render_template("forgotten-password.html", form=form)

    user = Backend.instance.get_user_from_login(form.login.data)
    success_message = _(
        "A password reset link has been sent at your email address. "
        "You should receive it within a few minutes."
    )
    if current_app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] and (
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

    request_ip = request.remote_addr or "unknown IP"
    success = True
    for email in user.emails:
        if not send_password_reset_mail(user, email):
            success = False
        current_app.logger.security(
            f"Sending a reset password mail to {email} for {user.user_name} from {request_ip}"
        )

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
    if not current_app.config["CANAILLE"]["ENABLE_PASSWORD_RECOVERY"]:
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
        Backend.instance.set_user_password(user, form.password.data)
        login_user(user)

        flash(_("Your password has been updated successfully"), "success")
        return redirect(
            session.pop(
                "redirect-after-login",
                url_for("core.account.profile_edition", edited_user=user),
            )
        )

    return render_template("reset-password.html", form=form, user=user, hash=hash)


@bp.route("/setup-2fa")
def setup_two_factor_auth():
    if not current_app.features.has_otp:
        abort(404)

    if current_user():
        return redirect(
            url_for("core.account.profile_edition", edited_user=current_user())
        )

    if "attempt_login_with_correct_password" not in session:
        flash(_("Cannot remember the login you attempted to sign in with"), "warning")
        return redirect(url_for("core.auth.login"))

    user = Backend.instance.get_user_from_login(
        session["attempt_login_with_correct_password"]
    )

    uri = user.get_otp_authentication_setup_uri()
    base64_qr_image = get_b64encoded_qr_image(uri)
    return render_template(
        "setup-2fa.html",
        secret=user.secret_token,
        qr_image=base64_qr_image,
        username=user.user_name,
    )


@bp.route("/verify-2fa", methods=["GET", "POST"])
def verify_two_factor_auth():
    if not current_app.features.has_otp:
        abort(404)

    if current_user():
        return redirect(
            url_for("core.account.profile_edition", edited_user=current_user())
        )

    if "attempt_login_with_correct_password" not in session:
        flash(_("Cannot remember the login you attempted to sign in with"), "warning")
        return redirect(url_for("core.auth.login"))

    form = TwoFactorForm(request.form or None)
    form.render_field_macro_file = "partial/login_field.html"

    if not request.form or form.form_control():
        return render_template(
            "verify-2fa.html",
            form=form,
            username=session["attempt_login_with_correct_password"],
        )

    user = Backend.instance.get_user_from_login(
        session["attempt_login_with_correct_password"]
    )

    if form.validate() and user.is_otp_valid(form.otp.data):
        welcome_message = (
            "Connection successful."
            if user.last_otp_login
            else "Two-factor authentication setup successful."
        )
        try:
            user.last_otp_login = datetime.datetime.now(datetime.timezone.utc)
            Backend.instance.save(user)
            request_ip = request.remote_addr or "unknown IP"
            current_app.logger.security(
                f'Succeed login attempt for {session["attempt_login_with_correct_password"]} from {request_ip}'
            )
            del session["attempt_login_with_correct_password"]
            login_user(user)
            flash(
                _(
                    "%(welcome_message)s Welcome %(user)s",
                    user=user.formatted_name,
                    welcome_message=welcome_message,
                ),
                "success",
            )
            return redirect(
                session.pop("redirect-after-login", url_for("core.account.index"))
            )
        except Exception:  # pragma: no cover
            flash("Two-factor authentication setup failed. Please try again.", "danger")
            return redirect(url_for("core.auth.verify_two_factor_auth"))
    else:
        flash(
            "The one-time password you entered is invalid. Please try again",
            "error",
        )
        request_ip = request.remote_addr or "unknown IP"
        current_app.logger.security(
            f'Failed login attempt (wrong OTP) for {session["attempt_login_with_correct_password"]} from {request_ip}'
        )
        return redirect(url_for("core.auth.verify_two_factor_auth"))
