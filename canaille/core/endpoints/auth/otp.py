import datetime

from flask import Blueprint
from flask import abort
from flask import current_app
from flask import flash
from flask import g
from flask import redirect
from flask import request
from flask import url_for

from canaille.app import get_b64encoded_qr_image
from canaille.app.i18n import gettext as _
from canaille.app.otp import get_otp_authentication_setup_uri
from canaille.app.otp import is_otp_valid
from canaille.app.otp import make_otp_secret
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.auth import auth_step
from canaille.core.auth import redirect_to_next_auth_step
from canaille.core.endpoints.forms import TwoFactorForm

bp = Blueprint("otp", __name__)


@bp.context_processor
def global_processor():
    return {
        "menu": False,
    }


@bp.route("/auth/otp", methods=["GET", "POST"])
@auth_step("otp")
def otp():
    if g.auth.user and not g.auth.user.last_otp_login:
        return redirect(url_for(".setup"))

    form = TwoFactorForm(request.form or None)
    form.render_field_macro_file = "core/partial/login_field.html"

    if not request.form or form.form_control():
        return render_template("core/auth/otp.html", form=form)

    if not form.validate() or not g.auth.user:
        flash(
            _("The passcode you entered is invalid. Please try again"),
            "error",
        )
        current_app.logger.security(f"Failed OTP authentication for {g.auth.user_name}")
        return render_template("core/auth/otp.html", form=form)

    otp_valid, hotp_counter = is_otp_valid(
        form.otp.data,
        current_app.config["CANAILLE"]["OTP_METHOD"],
        g.auth.user.secret_token,
        g.auth.user.hotp_counter,
    )
    if not otp_valid:
        flash(
            _("The passcode you entered is invalid. Please try again"),
            "error",
        )
        current_app.logger.security(f"Failed OTP authentication for {g.auth.user_name}")
        return render_template("core/auth/otp.html", form=form)

    g.auth.user.last_otp_login = datetime.datetime.now(datetime.timezone.utc)
    g.auth.user.hotp_counter = hotp_counter
    Backend.instance.save(g.auth.user)

    current_app.logger.security(f"Successful OTP authentication for {g.auth.user_name}")
    g.auth.set_step_finished("otp")
    return redirect_to_next_auth_step()


@bp.route("/auth/otp-setup", methods=["GET", "POST"])
def setup():
    if not current_app.features.has_otp:  # pragma: no cover
        abort(404)

    if not g.auth:
        flash(
            _("Cannot remember the login you attempted to sign in with."),
            "warning",
        )
        return redirect(
            url_for("core.account.profile_settings", edited_user=g.session.user)
            if g.session
            else url_for("core.auth.login")
        )

    if "otp_user_secret" not in g.auth.data:
        g.auth.data["otp_user_secret"] = make_otp_secret()

    form = TwoFactorForm(request.form or None)
    form.render_field_macro_file = "core/partial/login_field.html"
    uri, secret = get_otp_authentication_setup_uri(
        g.auth.user, g.auth.data["otp_user_secret"]
    )
    base64_qr_image = get_b64encoded_qr_image(uri)

    if not request.form or form.form_control():
        return render_template(
            "core/auth/setup-otp.html",
            secret=secret,
            qr_image=base64_qr_image,
            otp_uri=uri,
            form=form,
            menu=bool(g.session),
        )

    otp_valid, hotp_counter = is_otp_valid(
        form.otp.data,
        current_app.config["CANAILLE"]["OTP_METHOD"],
        g.auth.data["otp_user_secret"],
    )
    if not form.validate() or not otp_valid:
        flash(_("The passcode you entered is invalid. Please try again."), "error")
        return render_template(
            "core/auth/setup-otp.html",
            secret=secret,
            qr_image=base64_qr_image,
            otp_uri=uri,
            form=form,
            menu=bool(g.session),
        )

    g.auth.user.last_otp_login = datetime.datetime.now(datetime.timezone.utc)
    g.auth.user.secret_token = g.auth.data["otp_user_secret"]
    g.auth.user.hotp_counter = hotp_counter
    Backend.instance.save(g.auth.user)

    current_app.logger.security(
        f"OTP authentication factor reset for {g.auth.user.user_name}"
    )
    flash(_("Authenticator application correctly configured."), "success")

    g.auth.set_step_finished("otp")
    return redirect_to_next_auth_step()
