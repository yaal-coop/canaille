from flask import abort
from flask import current_app
from flask import flash
from flask import g
from flask import redirect
from flask import request
from flask import session
from flask import url_for

from canaille.app.flask import user_needed
from canaille.app.i18n import gettext as _
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.auth import AuthenticationSession

from . import bp


@bp.route("/profile/<user:edited_user>/auth/otp", methods=("GET", "POST"))
@user_needed()
def profile_auth_otp(user, edited_user):
    """Handle OTP authentication factor management."""
    if not user.can_manage_users and not (
        user.can_edit_self and edited_user.id == user.id
    ):
        abort(404)

    if not current_app.features.has_otp:
        abort(404)

    if "otp" not in current_app.config["CANAILLE"]["AUTHENTICATION_FACTORS"]:
        abort(404)

    menuitem = "profile" if user.id == edited_user.id else "users"
    action = request.form.get("action")

    if not edited_user.secret_token:
        session["redirect-after-login"] = url_for(
            "core.account.auth.profile_auth_otp",
            edited_user=edited_user,
        )
        g.auth = AuthenticationSession(
            user_name=g.session.user.user_name,
            welcome_flash=False,
            remaining=["otp"],
        )
        g.auth.save()
        return redirect(url_for("core.auth.otp.setup"))

    if request.method == "POST":
        if action == "otp-reset-confirm":
            return render_template(
                "core/modals/reset-otp.html", edited_user=edited_user
            )

        elif action == "otp-reset":
            flash(
                _("Authenticator application passcode authentication has been reset."),
                "success",
            )
            current_app.logger.security(
                f"Reset one-time passcode authentication for {edited_user.user_name} by {user.user_name}"
            )
            edited_user.secret_token = None
            edited_user.hotp_counter = None
            Backend.instance.save(edited_user)
            return redirect(
                url_for(
                    "core.account.auth.profile_auth_otp",
                    edited_user=edited_user,
                )
            )

    return render_template(
        "core/account/auth/otp.html",
        menuitem=menuitem,
        edited_user=edited_user,
    )
