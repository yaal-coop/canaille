from flask import Blueprint
from flask import current_app
from flask import flash
from flask import g
from flask import redirect
from flask import request
from flask import url_for

from canaille.app.i18n import gettext as _
from canaille.app.session import get_login_history
from canaille.app.session import logout_user
from canaille.app.session import remove_from_login_history
from canaille.app.templating import render_template
from canaille.core.auth import AuthenticationSession
from canaille.core.auth import get_user_from_login
from canaille.core.auth import login_placeholder
from canaille.core.auth import redirect_to_next_auth_step

from ..forms import LoginForm
from . import email
from . import otp
from . import password
from . import sms

bp = Blueprint("auth", __name__)
bp.register_blueprint(password.bp)
bp.register_blueprint(email.bp)
bp.register_blueprint(sms.bp)
bp.register_blueprint(otp.bp)


@bp.context_processor
def global_processor():
    return {
        "menu": False,
    }


@bp.before_request
def load_auth():
    g.auth = AuthenticationSession.load()


@bp.after_request
def save_auth(response):
    if "auth" in g and g.auth:
        g.auth.save()
    return response


@bp.route("/login", methods=("GET", "POST"))
@bp.route("/login/<username>", methods=("GET", "POST"))
def login(username=None):
    """Handle user login with optional account selection.

    When username is provided via URL, bypasses the login form and proceeds
    directly to authentication (password, OTP, etc.). Otherwise displays
    the login form with previously used accounts if available.

    :param username: Optional pre-selected username from URL path
    """
    if g.session:
        return redirect(
            url_for("core.account.profile_edition", edited_user=g.session.user)
        )

    g.auth = AuthenticationSession.update(user_name=username)
    g.auth.reset_auth_steps()

    if username:
        user = get_user_from_login(username)
        if user and not user.has_password() and current_app.features.has_smtp:
            return redirect(url_for("core.auth.password.firstlogin", user=user))

        return redirect_to_next_auth_step()

    form = LoginForm(request.form or None)
    form.render_field_macro_file = "core/partial/login_field.html"
    form["login"].render_kw["placeholder"] = login_placeholder()

    if not request.form or form.form_control():
        return render_template(
            "core/login.html",
            form=form,
            login_history=get_login_history(),
        )

    user = get_user_from_login(form.login.data)
    if user and not user.has_password() and current_app.features.has_smtp:
        return redirect(url_for("core.auth.password.firstlogin", user=user))

    if not form.validate():
        logout_user()
        flash(_("Login failed, please check your information"), "error")
        return render_template(
            "core/login.html", form=form, login_history=get_login_history()
        )

    g.auth = AuthenticationSession.update(
        user_name=form.login.data, remember=form.remember.data
    )
    return redirect_to_next_auth_step()


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


@bp.route("/forget/<username>")
def forget(username):
    """Remove a user from login history."""
    remove_from_login_history(username)
    return redirect(url_for(".login"))
