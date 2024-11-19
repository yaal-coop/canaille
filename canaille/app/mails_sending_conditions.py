from flask import current_app
from flask import flash

from canaille.app.i18n import gettext as _
from canaille.core.mails import send_compromised_password_check_failure_mail

from .flask import request_is_htmx


def check_if_send_mail_to_admins(form, api_url, hashed_password_suffix):
    if current_app.features.has_smtp and not request_is_htmx():
        current_app.logger.exception(
            "Password compromise investigation failed on HIBP API."
        )

        flash(
            _(
                "Password compromise investigation failed. "
                "Please contact the administrators."
            ),
            "error",
        )

        if form.user is not None:
            user_name = form.user.user_name
            user_email = form.user.emails[0]
        else:
            user_name = form["user_name"].data
            user_email = form["emails"].data[0]

        if send_compromised_password_check_failure_mail(
            api_url,
            user_name,
            user_email,
            hashed_password_suffix,
            current_app.config["CANAILLE"]["ADMIN_EMAIL"],
        ):
            flash(
                _(
                    "We have informed your administrator about the failure of the password compromise investigation."
                ),
                "success",
            )
        else:
            flash(
                _(
                    "An error occurred while communicating the incident to the administrators. "
                    "Please update your password as soon as possible. "
                    "If this still happens, please contact the administrators."
                ),
                "error",
            )
