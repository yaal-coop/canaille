import datetime

from flask import Blueprint
from flask import abort
from flask import current_app
from flask import flash
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
from canaille.app.session import current_user
from canaille.app.session import login_user
from canaille.app.session import logout_user
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.endpoints.forms import TwoFactorForm
from canaille.core.models import SEND_NEW_OTP_DELAY

from ..mails import send_password_initialization_mail
from ..mails import send_password_reset_mail
from .forms import FirstLoginForm
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
    if current_user():
        return redirect(
            url_for("core.account.profile_edition", edited_user=current_user())
        )

    form = LoginForm(request.form or None)
    form.render_field_macro_file = "core/partial/login_field.html"
    form["login"].render_kw["placeholder"] = Backend.instance.login_placeholder()

    if not request.form or form.form_control():
        return render_template("core/login.html", form=form)

    user = Backend.instance.get_user_from_login(form.login.data)
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
    if current_user():
        return redirect(
            url_for("core.account.profile_edition", edited_user=current_user())
        )

    if "attempt_login" not in session:
        flash(_("Cannot remember the login you attempted to sign in with"), "warning")
        return redirect(url_for("core.auth.login"))

    form = PasswordForm(request.form or None)
    form.render_field_macro_file = "core/partial/login_field.html"

    if not request.form or form.form_control():
        return render_template(
            "core/password.html", form=form, username=session["attempt_login"]
        )

    user = Backend.instance.get_user_from_login(session["attempt_login"])
    if user and not user.has_password() and current_app.features.has_smtp:
        return redirect(url_for("core.auth.firstlogin", user=user))

    if not form.validate() or not user:
        logout_user()
        flash(_("Login failed, please check your information"), "error")
        return render_template(
            "core/password.html", form=form, username=session["attempt_login"]
        )

    success, message = Backend.instance.check_user_password(user, form.password.data)
    request_ip = request.remote_addr or "unknown IP"
    if not success:
        logout_user()
        current_app.logger.security(
            f"Failed login attempt for {session['attempt_login']} from {request_ip}"
        )
        flash(message or _("Login failed, please check your information"), "error")
        return render_template(
            "core/password.html", form=form, username=session["attempt_login"]
        )

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
            user, otp_methods[0], request_ip, url_for("core.auth.password")
        )
    else:
        current_app.logger.security(
            f"Succeed login attempt for {session['attempt_login']} from {request_ip}"
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
        return render_template("core/firstlogin.html", form=form, user=user)

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

    return render_template("core/firstlogin.html", form=form)


@bp.route("/reset", methods=["GET", "POST"])
@smtp_needed()
def forgotten():
    if not current_app.config["CANAILLE"]["ENABLE_PASSWORD_RECOVERY"]:
        abort(404)

    form = ForgottenPasswordForm(request.form)
    if not request.form:
        return render_template("core/forgotten-password.html", form=form)

    if not form.validate():
        flash(_("Could not send the password reset link."), "error")
        return render_template("core/forgotten-password.html", form=form)

    user = Backend.instance.get_user_from_login(form.login.data)
    success_message = _(
        "A password reset link has been sent at your email address. "
        "You should receive it within a few minutes."
    )
    if current_app.config["CANAILLE"]["HIDE_INVALID_LOGINS"] and (
        not user or not user.can_edit_self
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

    return render_template("core/forgotten-password.html", form=form)


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

    return render_template("core/reset-password.html", form=form, user=user, hash=hash)


@bp.route("/setup-mfa")
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
        "core/setup-mfa.html",
        secret=user.secret_token,
        qr_image=base64_qr_image,
        user=user,
    )


@bp.route("/verify-mfa", methods=["GET", "POST"])
def verify_two_factor_auth():
    if current_user():
        return redirect(
            url_for("core.account.profile_edition", edited_user=current_user())
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

    user = Backend.instance.get_user_from_login(
        session["attempt_login_with_correct_password"]
    )

    if form.validate() and user.is_otp_valid(form.otp.data, current_otp_method):
        session["remaining_otp_methods"].pop(0)
        request_ip = request.remote_addr or "unknown IP"
        if session["remaining_otp_methods"]:
            return redirect_to_verify_mfa(
                user,
                session["remaining_otp_methods"][0],
                request_ip,
                url_for("core.auth.verify_two_factor_auth"),
            )
        else:
            user.last_otp_login = datetime.datetime.now(datetime.timezone.utc)
            Backend.instance.save(user)
            current_app.logger.security(
                f"Succeed login attempt for {session['attempt_login_with_correct_password']} from {request_ip}"
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
            return redirect(
                session.pop("redirect-after-login", url_for("core.account.index"))
            )
    else:
        flash(
            "The one-time password you entered is invalid. Please try again",
            "error",
        )
        request_ip = request.remote_addr or "unknown IP"
        current_app.logger.security(
            f"Failed login attempt (wrong OTP) for {session['attempt_login_with_correct_password']} from {request_ip}"
        )
        return redirect(url_for("core.auth.verify_two_factor_auth"))


@bp.route("/send-mail-otp", methods=["POST"])
def send_mail_otp():
    if not current_app.features.has_email_otp:
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

    if user.can_send_new_otp():
        if user.generate_and_send_otp_mail():
            Backend.instance.save(user)
            request_ip = request.remote_addr or "unknown IP"
            current_app.logger.security(
                f"Sent one-time password for {session['attempt_login_with_correct_password']} to {user.emails[0]} from {request_ip}"
            )
            flash(
                "Code successfully sent!",
                "success",
            )
        else:
            flash("Error while sending one-time password. Please try again.", "danger")
    else:
        flash(
            f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds.",
            "danger",
        )

    return redirect(url_for("core.auth.verify_two_factor_auth"))


@bp.route("/send-sms-otp", methods=["POST"])
def send_sms_otp():
    if not current_app.features.has_sms_otp:
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

    if user.can_send_new_otp():
        if user.generate_and_send_otp_sms():
            Backend.instance.save(user)
            request_ip = request.remote_addr or "unknown IP"
            current_app.logger.security(
                f"Sent one-time password for {session['attempt_login_with_correct_password']} to {user.phone_numbers[0]} from {request_ip}"
            )
            flash(
                "Code successfully sent!",
                "success",
            )
        else:
            flash("Error while sending one-time password. Please try again.", "danger")
    else:
        flash(
            f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds.",
            "danger",
        )

    return redirect(url_for("core.auth.verify_two_factor_auth"))


def redirect_to_verify_mfa(user, otp_method, request_ip, fail_redirect_url):
    if otp_method in ["HOTP", "TOTP"]:
        if not user.last_otp_login:
            flash(
                "You have not enabled multi-factor authentication. Please enable it first to login.",
                "info",
            )
            return redirect(url_for("core.auth.setup_two_factor_auth"))
        flash(
            "Please enter the one-time password from your authenticator app.",
            "info",
        )
        return redirect(url_for("core.auth.verify_two_factor_auth"))
    elif otp_method == "EMAIL_OTP":
        if user.can_send_new_otp():
            if user.generate_and_send_otp_mail():
                Backend.instance.save(user)
                flash(
                    f"A one-time password has been sent to your email address {mask_email(user.emails[0])}. Please enter it below to login.",
                    "info",
                )
                current_app.logger.security(
                    f"Sent one-time password for {session['attempt_login_with_correct_password']} to {user.emails[0]} from {request_ip}"
                )
                return redirect(url_for("core.auth.verify_two_factor_auth"))
            else:
                flash(
                    "Error while sending one-time password. Please try again.", "danger"
                )
                return redirect(fail_redirect_url)
        else:
            flash(
                f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds.",
                "danger",
            )
            return redirect(fail_redirect_url)
    else:  # sms
        if user.can_send_new_otp():
            if user.generate_and_send_otp_sms():
                Backend.instance.save(user)
                flash(
                    f"A one-time password has been sent to your phone number {mask_phone(user.phone_numbers[0])}. Please enter it below to login.",
                    "info",
                )
                current_app.logger.security(
                    f"Sent one-time password for {session['attempt_login_with_correct_password']} to {user.phone_numbers[0]} from {request_ip}"
                )
                return redirect(url_for("core.auth.verify_two_factor_auth"))
            else:
                flash(
                    "Error while sending one-time password. Please try again.",
                    "danger",
                )
                return redirect(fail_redirect_url)
        else:
            flash(
                f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds.",
                "danger",
            )
            return redirect(fail_redirect_url)
