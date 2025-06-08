import datetime

from flask import Blueprint
from flask import current_app
from flask import flash
from flask import g
from flask import redirect
from flask import request
from flask import url_for

from canaille.app.i18n import gettext as _
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.auth import auth_step
from canaille.core.auth import redirect_to_next_auth_step
from canaille.core.endpoints.forms import TwoFactorForm
from canaille.core.models import SEND_NEW_OTP_DELAY
from canaille.core.sms import send_one_time_password_sms

bp = Blueprint("sms", __name__)


@bp.context_processor
def global_processor():
    return {
        "menu": False,
    }


@bp.route("/auth/sms", methods=["GET", "POST"])
@auth_step("sms")
def sms():
    # Automatically send a passcode when users access the form for the first time
    if g.auth.user and (
        not g.auth.user.one_time_password_emission_date
        or g.auth.current_step_start_dt > g.auth.user.one_time_password_emission_date
    ):
        send_sms_otp(flashes=False)

    form = TwoFactorForm(request.form or None)
    form.render_field_macro_file = "core/partial/login_field.html"
    resend_delay = (
        g.auth.user.next_otp_send_delay
        if g.auth.user
        else datetime.timedelta(seconds=SEND_NEW_OTP_DELAY)
    )

    if not request.form or form.form_control():
        return render_template(
            "core/auth/sms.html", form=form, resend_delay=resend_delay
        )

    if request.form.get("action") == "resend":
        send_sms_otp()
        return redirect(url_for(".sms"))

    if (
        not form.validate()
        or not g.auth.user
        or not g.auth.user.is_email_or_sms_otp_valid(form.otp.data)
    ):
        flash(_("The passcode you entered is invalid. Please try again"), "error")
        current_app.logger.security(
            f"Failed sms code authentication for {g.auth.user_name}"
        )
        return render_template(
            "core/auth/sms.html", form=form, resend_delay=resend_delay
        )

    current_app.logger.security(
        f"Successful sms code authentication for {g.auth.user_name}"
    )
    g.auth.set_step_finished("sms")
    return redirect_to_next_auth_step()


def send_sms_otp(flashes=True):
    if g.auth.user:
        if not g.auth.user.can_send_new_otp():
            if flashes:
                flash(
                    _(
                        f"Too many attempts. Please try again in {SEND_NEW_OTP_DELAY} seconds."
                    ),
                    "danger",
                )
            return

        otp = g.auth.user.generate_sms_or_mail_otp()
        if send_one_time_password_sms(g.auth.user.preferred_email, otp):
            Backend.instance.save(g.auth.user)
            phone_number = g.auth.user.phone_numbers[0]
            current_app.logger.security(
                f"Sent one-time passcode for {g.auth.user_name} at {phone_number}"
            )
    if flashes:
        flash(_("The new verification code have been sent."), "success")
