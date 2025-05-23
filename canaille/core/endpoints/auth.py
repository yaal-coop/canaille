import datetime

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
from canaille.app import get_b64encoded_qr_image
from canaille.app import mask_email
from canaille.app import mask_phone
from canaille.app.flask import smtp_needed
from canaille.app.i18n import gettext as _
from canaille.app.session import login_user
from canaille.app.session import logout_user
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.auth import get_user_from_login
from canaille.core.auth import login_placeholder
from canaille.core.endpoints.forms import TwoFactorForm
from canaille.core.models import SEND_NEW_OTP_DELAY

from ..mails import send_password_initialization_mail
from ..mails import send_password_reset_mail
from .forms import FirstLoginForm
from .forms import ForgottenPasswordCodeForm
from .forms import ForgottenPasswordForm
from .forms import LoginForm
from .forms import PasswordForm
from .forms import PasswordResetForm

bp = Blueprint("auth", __name__)


@bp.context_processor
def global_processor():
    return {
        "menu": False,
    }


@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.session:
        return redirect(
            url_for("core.account.profile_edition", edited_user=g.session.user)
        )

    form = LoginForm(request.form or None)
    form.render_field_macro_file = "core/partial/login_field.html"
    form["login"].render_kw["placeholder"] = login_placeholder()

    if not request.form or form.form_control():
        return render_template("core/login.html", form=form)

    user = get_user_from_login(form.login.data)
    if user and not user.has_password() and current_app.features.has_smtp:
        return redirect(url_for("core.auth.firstlogin", user=user))

    if not form.validate():
        logout_user()
        flash(_("Login failed, please check your information"), "error")
        return render_template("core/login.html", form=form)

    session["attempt_login"] = form.login.data
    return redirect(url_for("core.auth.password"))


@bp.route("/password", methods=("GET", "POST"))
def password():
    if "attempt_login" not in session and (not g.session or not g.session.user):
        flash(_("Cannot remember the login you attempted to sign in with"), "warning")
        return redirect(url_for("core.auth.login"))

    username = (
        session["attempt_login"]
        if "attempt_login" in session
        else g.session.user.user_name
    )

    form = PasswordForm(request.form or None)
    form.render_field_macro_file = "core/partial/login_field.html"

    if not request.form or form.form_control():
        return render_template("core/password.html", form=form, username=username)

    user = (g.session and g.session.user) or get_user_from_login(
        session["attempt_login"]
    )
    if user and not user.has_password() and current_app.features.has_smtp:
        return redirect(url_for("core.auth.firstlogin", user=user))

    if not form.validate() or not user:
        logout_user()
        flash(_("Login failed, please check your information"), "error")
        return render_template("core/password.html", form=form, username=username)

    success, message = Backend.instance.check_user_password(user, form.password.data)
    if not success:
        logout_user()
        current_app.logger.security(
            f"Failed login attempt for {session['attempt_login']}"
        )
        flash(message or _("Login failed, please check your information"), "error")
        return render_template("core/password.html", form=form, username=username)

    otp_methods = []
    if current_app.features.has_otp:
        otp_methods.append(current_app.features.otp_method)  # TOTP or HOTP
    if current_app.features.has_email_otp:
        otp_methods.append("EMAIL_OTP")
    if current_app.features.has_sms_otp:
        otp_methods.append("SMS_OTP")

    if otp_methods:
        session["remaining_otp_methods"] = otp_methods
        session["attempt_login_with_correct_password"] = session.pop("attempt_login")
        return redirect_to_verify_mfa(
            user, otp_methods[0], url_for("core.auth.password")
        )

    current_app.logger.security(f"Succeed login attempt for {username}")
    if "attempt_login" in session:
        del session["attempt_login"]

    login_user(user)
    flash(
        _("Connection successful. Welcome %(user)s", user=user.name),
        "success",
    )
    return redirect(session.pop("redirect-after-login", url_for("core.account.index")))


@bp.route("/logout")
def logout():
    if user := g.session and g.session.user:
        current_app.logger.security(f"Logout {user.identifier}")

        flash(
            _(
                "You have been disconnected. See you next time %(user)s",
                user=user.name,
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
        return render_template("core/firstlogin.html", form=form, user=user)

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

    return render_template("core/firstlogin.html", form=form)


@bp.route("/reset", methods=["GET", "POST"])
@smtp_needed()
def forgotten():
    if not current_app.config["CANAILLE"]["ENABLE_PASSWORD_RECOVERY"]:
        abort(404)

    form = ForgottenPasswordForm(request.form)
    if not request.form:
        return render_template("core/forgotten-password.html", form=form)

    item_name = "link" if current_app.features.has_trusted_hosts else "code"

    if not form.validate():
        flash(_(f"Could not send the password reset {item_name}."), "error")
        return render_template("core/forgotten-password.html", form=form)

    user = get_user_from_login(form.login.data)
    success_message = _(
        f"A password reset {item_name} has been sent at your email address. "
        "You should receive it within a few minutes."
    )
    if current_app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] and (
        not user or not user.can_edit_self or user.locked
    ):
        flash(success_message, "success")
        return render_template("core/forgotten-password.html", form=form)

    if not user.can_edit_self:
        flash(
            _(
                "The user '%(user)s' does not have permissions to update their password. "
                "We cannot send a password reset email.",
                user=user.formatted_name,
            ),
            "error",
        )
        return render_template("core/forgotten-password.html", form=form)

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
        return render_template("core/forgotten-password.html", form=form)
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
        return render_template("core/forgotten-password-code.html", form=form)

    if not form.validate() or not user.is_otp_valid(form.code.data, "EMAIL_OTP"):
        flash(_("Invalid code."), "error")
        return render_template("core/forgotten-password-code.html", form=form)

    return redirect(url_for(".reset", user=user, token=form.code.data))


@bp.route("/reset/<user:user>/<token>", methods=["GET", "POST"])
def reset(user, token):
    if not current_app.config["CANAILLE"]["ENABLE_PASSWORD_RECOVERY"]:
        abort(404)
    form = PasswordResetForm(request.form)

    if current_app.features.has_trusted_hosts:
        token = build_hash(token)

    if not user or not user.is_otp_valid(token, "EMAIL_OTP"):
        item_name = "link" if current_app.features.has_trusted_hosts else "code"
        flash(
            _(f"The password reset {item_name} that brought you here was invalid."),
            "error",
        )
        return redirect(url_for("core.account.index"))

    if not request.form or not form.validate():
        return render_template(
            "core/reset-password.html", form=form, user=user, token=token
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


@bp.route("/setup-otp")
def setup_otp_auth():
    if not current_app.features.has_otp:
        abort(404)

    from canaille.app.otp import get_otp_authentication_setup_uri

    if g.session:
        return redirect(
            url_for("core.account.profile_edition", edited_user=g.session.user)
        )

    if "attempt_login_with_correct_password" not in session:
        flash(_("Cannot remember the login you attempted to sign in with"), "warning")
        return redirect(url_for("core.auth.login"))

    user = get_user_from_login(session["attempt_login_with_correct_password"])

    uri, secret = get_otp_authentication_setup_uri(user)
    base64_qr_image = get_b64encoded_qr_image(uri)
    return render_template(
        "core/setup-otp.html",
        secret=secret,
        qr_image=base64_qr_image,
        otp_uri=uri,
        user=user,
    )


@bp.route("/verify-mfa", methods=["GET", "POST"])
def verify_two_factor_auth():
    if g.session:
        return redirect(
            url_for("core.account.profile_edition", edited_user=g.session.user)
        )

    if (
        "attempt_login_with_correct_password" not in session
        or "remaining_otp_methods" not in session
        or not session["remaining_otp_methods"]
    ):
        flash(_("Cannot remember the login you attempted to sign in with"), "warning")
        return redirect(url_for("core.auth.login"))

    current_otp_method = session["remaining_otp_methods"][0]
    if (
        (current_otp_method in ["TOTP", "HOTP"] and not current_app.features.has_otp)
        or (
            current_otp_method == "EMAIL_OTP" and not current_app.features.has_email_otp
        )
        or (current_otp_method == "SMS_OTP" and not current_app.features.has_sms_otp)
    ):
        abort(404)

    form = TwoFactorForm(request.form or None)
    form.render_field_macro_file = "core/partial/login_field.html"

    if not request.form or form.form_control():
        return render_template(
            "core/verify-mfa.html",
            form=form,
            username=session["attempt_login_with_correct_password"],
            method=current_otp_method,
        )

    user = get_user_from_login(session["attempt_login_with_correct_password"])

    if not form.validate() or not user.is_otp_valid(form.otp.data, current_otp_method):
        flash(
            _("The passcode you entered is invalid. Please try again"),
            "error",
        )
        current_app.logger.security(
            f"Failed login attempt (wrong OTP) for {session['attempt_login_with_correct_password']}"
        )
        return redirect(url_for("core.auth.verify_two_factor_auth"))

    session["remaining_otp_methods"].pop(0)
    if session["remaining_otp_methods"]:
        return redirect_to_verify_mfa(
            user,
            session["remaining_otp_methods"][0],
            url_for("core.auth.verify_two_factor_auth"),
        )

    user.last_otp_login = datetime.datetime.now(datetime.timezone.utc)
    Backend.instance.save(user)
    current_app.logger.security(
        f"Succeed login attempt for {session['attempt_login_with_correct_password']}"
    )
    del session["attempt_login_with_correct_password"]
    login_user(user)
    flash(
        _(
            "Connection successful. Welcome %(user)s",
            user=user.formatted_name,
        ),
        "success",
    )
    return redirect(session.pop("redirect-after-login", url_for("core.account.index")))


@bp.route("/send-mail-otp", methods=["POST"])
def send_mail_otp():
    if not current_app.features.has_email_otp:
        abort(404)

    if g.session:
        return redirect(
            url_for("core.account.profile_edition", edited_user=g.session.user)
        )

    if "attempt_login_with_correct_password" not in session:
        flash(_("Cannot remember the login you attempted to sign in with"), "warning")
        return redirect(url_for("core.auth.login"))

    user = get_user_from_login(session["attempt_login_with_correct_password"])

    if not user.can_send_new_otp():
        flash(
            _(f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds."),
            "danger",
        )

    elif not user.generate_and_send_otp_mail():
        flash(
            _("Error while sending the passcode by email. Please try again."),
            "danger",
        )

    else:
        Backend.instance.save(user)
        current_app.logger.security(
            f"Sent one-time passcode for {session['attempt_login_with_correct_password']} to {user.preferred_email}"
        )
        flash(
            _("Passcode successfully sent!"),
            "success",
        )

    return redirect(url_for("core.auth.verify_two_factor_auth"))


@bp.route("/send-sms-otp", methods=["POST"])
def send_sms_otp():
    if not current_app.features.has_sms_otp:
        abort(404)

    if g.session:
        return redirect(
            url_for("core.account.profile_edition", edited_user=g.session.user)
        )

    if "attempt_login_with_correct_password" not in session:
        flash(_("Cannot remember the login you attempted to sign in with"), "warning")
        return redirect(url_for("core.auth.login"))

    user = get_user_from_login(session["attempt_login_with_correct_password"])

    if not user.can_send_new_otp():
        flash(
            _(f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds."),
            "danger",
        )

    elif not user.generate_and_send_otp_sms():
        flash(
            _("Error while sending the passcode by SMS. Please try again."),
            "danger",
        )

    else:
        Backend.instance.save(user)
        current_app.logger.security(
            f"Sent one-time passcode for {session['attempt_login_with_correct_password']} to {user.phone_numbers[0]}"
        )
        flash(
            _("Passcode successfully sent!"),
            "success",
        )

    return redirect(url_for("core.auth.verify_two_factor_auth"))


def verify_hotp_totp(user):
    if not user.last_otp_login:
        flash(
            _(
                "In order to continue logging in, you need to configure an authenticator application."
            ),
            "info",
        )
        return redirect(url_for("core.auth.setup_otp_auth"))

    flash(
        _("Please enter the passcode from your authenticator application."),
        "info",
    )
    return redirect(url_for("core.auth.verify_two_factor_auth"))


def verify_email_otp(user, fail_redirect_url):
    if not user.can_send_new_otp():
        flash(
            _(f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds."),
            "danger",
        )
        return redirect(fail_redirect_url)

    if not user.generate_and_send_otp_mail():
        flash(
            _("Error while sending passcode by email. Please try again."),
            "danger",
        )
        return redirect(fail_redirect_url)

    Backend.instance.save(user)
    email = mask_email(user.preferred_email)
    flash(
        _(
            f"A passcode has been sent to your email address {email}. Please enter it below to login."
        ),
        "info",
    )
    current_app.logger.security(
        f"Sent one-time passcode for {session['attempt_login_with_correct_password']} to {user.preferred_email}"
    )
    return redirect(url_for("core.auth.verify_two_factor_auth"))


def verify_sms_otp(user, fail_redirect_url):
    if not user.can_send_new_otp():
        flash(
            _(f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds."),
            "danger",
        )
        return redirect(fail_redirect_url)

    if not user.generate_and_send_otp_sms():
        flash(
            _("Error while sending the passcode by SMS. Please try again."),
            "danger",
        )
        return redirect(fail_redirect_url)

    Backend.instance.save(user)
    phone_number = mask_phone(user.phone_numbers[0])
    flash(
        _(
            f"A passcode has been sent to your phone number {phone_number}. Please enter it below to login."
        ),
        "info",
    )
    current_app.logger.security(
        f"Sent one-time passcode for {session['attempt_login_with_correct_password']} to {user.phone_numbers[0]}"
    )
    return redirect(url_for("core.auth.verify_two_factor_auth"))


def redirect_to_verify_mfa(user, otp_method, fail_redirect_url):
    if otp_method in ["HOTP", "TOTP"]:
        return verify_hotp_totp(user)

    elif otp_method == "EMAIL_OTP":
        return verify_email_otp(user, fail_redirect_url)

    else:
        return verify_sms_otp(user, fail_redirect_url)
