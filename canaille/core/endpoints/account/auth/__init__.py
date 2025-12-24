from flask import Blueprint
from flask import abort
from flask import current_app
from flask import redirect
from flask import url_for

from canaille.app.flask import user_needed
from canaille.app.templating import render_template

bp = Blueprint("auth", __name__)


def _get_available_factor_ids():
    """Return the list of available authentication factor IDs."""
    configured = current_app.config["CANAILLE"]["AUTHENTICATION_FACTORS"]
    factors = []
    if "password" in configured:
        factors.append("password")
    if current_app.features.has_otp and "otp" in configured:
        factors.append("otp")
    if current_app.features.has_fido and "fido2" in configured:
        factors.append("fido2")
    return factors


@bp.route("/profile/<user:edited_user>/auth")
@user_needed()
def profile_auth(user, edited_user):
    """Display the authentication factors management page."""
    if not user.can_manage_users and not (
        user.can_edit_self and edited_user.id == user.id
    ):
        abort(404)

    factors = _get_available_factor_ids()

    if len(factors) == 1:
        return redirect(
            url_for(
                f"core.account.auth.profile_auth_{factors[0]}", edited_user=edited_user
            )
        )

    menuitem = "profile" if user.id == edited_user.id else "users"
    return render_template(
        "core/account/auth/index.html",
        menuitem=menuitem,
        edited_user=edited_user,
    )


from . import fido2  # noqa: E402, F401
from . import otp  # noqa: E402, F401
from . import password  # noqa: E402, F401
