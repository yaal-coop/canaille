from flask import abort
from flask import current_app
from flask import flash
from flask import redirect
from flask import request
from flask import url_for
from werkzeug.datastructures import CombinedMultiDict

from canaille.app.flask import request_is_partial
from canaille.app.flask import user_needed
from canaille.app.i18n import gettext as _
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.endpoints.forms import build_profile_form
from canaille.core.mails import send_password_initialization_mail
from canaille.core.mails import send_password_reset_mail

from . import bp


@bp.route("/profile/<user:edited_user>/auth/password", methods=("GET", "POST"))
@user_needed()
def profile_auth_password(user, edited_user):
    """Handle password authentication factor management."""
    if not user.can_manage_users and not (
        user.can_edit_self and edited_user.id == user.id
    ):
        abort(404)

    if "password" not in current_app.config["CANAILLE"]["AUTHENTICATION_FACTORS"]:
        abort(404)

    menuitem = "profile" if user.id == edited_user.id else "users"
    available_fields = {"password"}
    data = {}

    form = build_profile_form(
        user.writable_fields & available_fields,
        user.readable_fields & available_fields,
        edited_user,
    )
    form.process(CombinedMultiDict((request.files, request.form)) or None, data=data)

    action = request.form.get("action")

    if request.method == "POST":
        if action in ("password-initialization-mail", "password-reset-mail"):
            return _handle_password_mail(edited_user, action)

        if action == "edit-password" or request_is_partial():
            if not form.validate():
                flash(
                    _(
                        "Your changes couldn't be saved. "
                        "Please check the form and try again."
                    ),
                    "error",
                )
            else:
                if "password1" in request.form and form["password1"].data:
                    Backend.instance.set_user_password(
                        edited_user, form["password1"].data
                    )
                    current_app.logger.security(
                        f"Changed password in settings for {edited_user.user_name}"
                    )
                    Backend.instance.save(edited_user)
                    flash(_("Password updated successfully."), "success")
                    return redirect(
                        url_for(
                            "core.account.auth.profile_auth_password",
                            edited_user=edited_user,
                        )
                    )

    return render_template(
        "core/account/auth/password.html",
        form=form,
        menuitem=menuitem,
        edited_user=edited_user,
    )


def _handle_password_mail(edited_user, action):
    """Handle password initialization and reset mail sending."""
    if action == "password-initialization-mail":
        for email in edited_user.emails or []:
            send_password_initialization_mail(edited_user, email)
        flash(
            _(
                "Sending password initialization link at the user email address. "
                "It should be received within a few minutes."
            ),
            "info",
        )
    else:  # password-reset-mail
        for email in edited_user.emails or []:
            send_password_reset_mail(edited_user, email)
        flash(
            _(
                "Sending password reset link to the user email address. "
                "It should be received within a few minutes."
            ),
            "info",
        )
    return redirect(
        url_for(
            "core.account.auth.profile_auth_password",
            edited_user=edited_user,
        )
    )
