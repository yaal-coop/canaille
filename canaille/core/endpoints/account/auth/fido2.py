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


def _find_credential(edited_user, credential_id):
    """Find a credential by ID in the user's webauthn credentials."""
    for cred in edited_user.webauthn_credentials:
        if str(cred.id) == credential_id:
            return cred
    return None


def _redirect_to_fido2_page(edited_user):
    return redirect(
        url_for("core.account.auth.profile_auth_fido2", edited_user=edited_user)
    )


def _handle_confirm_delete(edited_user, credential_id):
    """Show confirmation modal for deleting a credential."""
    credential = _find_credential(edited_user, credential_id)
    if not credential:
        flash(_("Credential not found."), "error")
        return _redirect_to_fido2_page(edited_user)
    return render_template(
        "core/modals/delete-credential.html",
        edited_user=edited_user,
        credential_id=credential_id,
        credential_name=credential.name,
    )


def _handle_rename(user, edited_user, credential_id):
    """Rename a credential."""
    new_name = request.form.get(f"credential_name_{credential_id}", "").strip()
    if not new_name:
        flash(_("Name cannot be empty."), "error")
        return _redirect_to_fido2_page(edited_user)

    credential = _find_credential(edited_user, credential_id)
    if not credential:
        flash(_("Credential not found."), "error")
        return _redirect_to_fido2_page(edited_user)

    credential.name = new_name
    Backend.instance.save(credential)
    flash(_("The passkey has been renamed."), "success")
    current_app.logger.security(
        f"Renamed WebAuthn credential {credential_id} for {edited_user.user_name} by {user.user_name}"
    )
    return _redirect_to_fido2_page(edited_user)


def _handle_reset(user, edited_user):
    """Delete all credentials."""
    for credential in list(edited_user.webauthn_credentials):
        Backend.instance.delete(credential)
    flash(_("All passkeys have been removed."), "success")
    current_app.logger.security(
        f"Reset all WebAuthn credentials for {edited_user.user_name} by {user.user_name}"
    )
    return _redirect_to_fido2_page(edited_user)


def _handle_delete(user, edited_user):
    """Delete a single credential."""
    credential_id = request.form.get("credential_id")
    if not credential_id:
        flash(_("Credential not found."), "error")
        return _redirect_to_fido2_page(edited_user)

    credential = _find_credential(edited_user, credential_id)
    if credential:
        Backend.instance.delete(credential)
        flash(_("The passkey has been removed."), "success")
        current_app.logger.security(
            f"Deleted WebAuthn credential {credential_id} for {edited_user.user_name} by {user.user_name}"
        )
    else:
        flash(_("Credential not found."), "error")
    return _redirect_to_fido2_page(edited_user)


def _handle_setup(edited_user):
    """Redirect to FIDO2 setup flow."""
    session["redirect-after-login"] = url_for(
        "core.account.auth.profile_auth_fido2",
        edited_user=edited_user,
    )
    g.auth = AuthenticationSession(
        user_name=g.session.user.user_name,
        welcome_flash=False,
        remaining=["fido2"],
    )
    g.auth.save()
    response = redirect(url_for("core.auth.fido2.setup"))
    response.headers["HX-Redirect"] = url_for("core.auth.fido2.setup")
    return response


@bp.route("/profile/<user:edited_user>/auth/fido2", methods=("GET", "POST"))
@user_needed()
def profile_auth_fido2(user, edited_user):
    """Handle FIDO2/WebAuthn authentication factor management."""
    if not user.can_manage_users and not (
        user.can_edit_self and edited_user.id == user.id
    ):
        abort(404)

    if not current_app.features.has_fido:
        abort(404)

    if "fido2" not in current_app.config["CANAILLE"]["AUTHENTICATION_FACTORS"]:
        abort(404)

    menuitem = "profile" if user.id == edited_user.id else "users"
    action = request.form.get("action")

    if not edited_user.webauthn_credentials and action != "fido2-setup":
        return _handle_setup(edited_user)

    if request.method == "POST":
        credential_id = request.form.get("fido2-confirm-credential")
        if credential_id:
            return _handle_confirm_delete(edited_user, credential_id)

        credential_id = request.form.get("fido2-rename-credential")
        if credential_id:
            return _handle_rename(user, edited_user, credential_id)

        if action == "fido2-reset-confirm":
            return render_template(
                "core/modals/reset-fido.html", edited_user=edited_user
            )

        if action == "fido2-reset":
            return _handle_reset(user, edited_user)

        if action == "fido2-delete-credential":
            return _handle_delete(user, edited_user)

        if action == "fido2-setup":
            return _handle_setup(edited_user)

    return render_template(
        "core/account/auth/fido2.html",
        menuitem=menuitem,
        edited_user=edited_user,
    )
