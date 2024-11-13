from flask import current_app
from flask import flash

from canaille.app import models
from canaille.app.i18n import gettext as _
from canaille.backends import Backend
from canaille.core.mails import send_compromised_password_check_failure_mail

from .flask import request_is_htmx


def check_if_send_mail_to_admins(form, api_url, hashed_password_suffix):
    if current_app.features.has_smtp and not request_is_htmx():
        flash(
            _(
                "Password compromise investigation failed. "
                "Please contact the administrators."
            ),
            "error",
        )

        group_user = Backend.instance.query(models.User)

        if (
            current_app.config["CANAILLE"]["ACL"]
            and current_app.config["CANAILLE"]["ACL"]["ADMIN"]
            and current_app.config["CANAILLE"]["ACL"]["ADMIN"]["FILTER"]
            and current_app.config["CANAILLE"]["ACL"]["ADMIN"]["FILTER"]["groups"]
        ):
            admin_group_display_name = current_app.config["CANAILLE"]["ACL"]["ADMIN"][
                "FILTER"
            ]["groups"]

            admin_emails = [
                user.emails[0]
                for user in group_user
                if any(
                    group.display_name == admin_group_display_name
                    for group in user.groups
                )
            ]
        else:
            admin_emails = [current_app.config["CANAILLE"]["ADMIN_EMAIL"]]

        if form.user is not None:
            user_name = form.user.user_name
            user_email = form.user.emails[0]
        else:
            user_name = form["user_name"].data
            user_email = form["emails"].data[0]

        number_emails_send = 0

        for email in admin_emails:
            if send_compromised_password_check_failure_mail(
                api_url, user_name, user_email, hashed_password_suffix, email
            ):
                number_emails_send += 1
            else:
                pass

        if number_emails_send > 0:
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
            return None

        return number_emails_send
    return None
