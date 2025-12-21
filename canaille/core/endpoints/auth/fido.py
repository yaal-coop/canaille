import datetime
import uuid

from flask import Blueprint
from flask import abort
from flask import current_app
from flask import flash
from flask import g
from flask import jsonify
from flask import redirect
from flask import request
from flask import session
from flask import url_for
from webauthn import generate_authentication_options
from webauthn import generate_registration_options
from webauthn import options_to_json
from webauthn import verify_authentication_response
from webauthn import verify_registration_response
from webauthn.helpers.base64url_to_bytes import base64url_to_bytes
from webauthn.helpers.bytes_to_base64url import bytes_to_base64url
from webauthn.helpers.exceptions import InvalidAuthenticationResponse
from webauthn.helpers.exceptions import InvalidRegistrationResponse
from webauthn.helpers.structs import AttestationConveyancePreference
from webauthn.helpers.structs import AuthenticatorSelectionCriteria
from webauthn.helpers.structs import PublicKeyCredentialDescriptor
from webauthn.helpers.structs import UserVerificationRequirement

from canaille.app import models
from canaille.app.fido import deserialize_transports
from canaille.app.fido import get_origin
from canaille.app.fido import get_rp_id
from canaille.app.fido import get_rp_name
from canaille.app.fido import serialize_transports
from canaille.app.flask import csrf
from canaille.app.i18n import gettext as _
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.auth import AuthenticationSession
from canaille.core.auth import auth_step
from canaille.core.auth import redirect_to_next_auth_step

bp = Blueprint("fido2", __name__)


@bp.context_processor
def global_processor():
    show_menu = bool(
        g.get("session") and g.get("auth") and g.session.user == g.auth.user
    )
    return {
        "menu": show_menu,
    }


@bp.route("/auth/fido2", methods=("GET", "POST"))
@auth_step("fido2")
@csrf.exempt
def webauthn():
    if not current_app.features.has_fido:
        abort(404)

    if g.auth.user and not g.auth.user.has_webauthn_credential():
        return redirect(url_for(".setup"))

    if request.method == "GET":
        return generate_auth_options()

    return verify_auth_response()


def generate_auth_options():
    """Generate WebAuthn authentication options (challenge)."""
    rp_id = get_rp_id()

    allowed_credentials = []
    for credential in g.auth.user.webauthn_credentials:
        transports = (
            deserialize_transports(credential.transports)
            if credential.transports
            else None
        )
        descriptor = PublicKeyCredentialDescriptor(
            id=credential.credential_id, transports=transports
        )
        allowed_credentials.append(descriptor)

    timeout_ms = int(
        current_app.config["CANAILLE"]["FIDO_TIMEOUT"].total_seconds() * 1000
    )
    options = generate_authentication_options(
        rp_id=rp_id,
        timeout=timeout_ms,
        allow_credentials=allowed_credentials,
        user_verification=UserVerificationRequirement(
            current_app.config["CANAILLE"]["FIDO_USER_VERIFICATION"]
        ),
    )

    g.auth.data["fido_challenge"] = bytes_to_base64url(options.challenge)
    g.auth.save()

    return render_template(
        "core/auth/fido.html",
        options_json=options_to_json(options),
    )


def verify_auth_response():
    """Verify WebAuthn authentication response."""
    challenge = g.auth.data.get("fido_challenge")
    if not challenge:
        return jsonify({"success": False, "error": "No challenge found"}), 400

    credential_data = request.get_json()
    if not credential_data:
        return jsonify({"success": False, "error": "Invalid JSON"}), 400

    try:
        credential_raw_id = base64url_to_bytes(credential_data["rawId"])
    except (KeyError, ValueError) as e:
        return jsonify({"success": False, "error": f"Invalid credential ID: {e}"}), 400

    credential = next(
        (
            c
            for c in g.auth.user.webauthn_credentials
            if c.credential_id == credential_raw_id
        ),
        None,
    )
    if not credential:
        return jsonify({"success": False, "error": "Credential not found"}), 400

    try:
        verification = verify_authentication_response(
            credential=credential_data,
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=get_rp_id(),
            expected_origin=get_origin(),
            credential_public_key=credential.public_key,
            credential_current_sign_count=credential.sign_count,
            require_user_verification=current_app.config["CANAILLE"][
                "FIDO_USER_VERIFICATION"
            ]
            == "required",
        )
    except InvalidAuthenticationResponse as e:
        current_app.logger.security(
            f"Failed WebAuthn authentication for {g.auth.user_name}: {e}"
        )
        return jsonify({"success": False, "error": str(e)}), 400

    credential.sign_count = verification.new_sign_count
    credential.last_used_at = datetime.datetime.now(datetime.timezone.utc)
    Backend.instance.save(credential)

    current_app.logger.security(
        f"Successful WebAuthn authentication for {g.auth.user_name}"
    )
    g.auth.set_step_finished("fido2")

    redirect_response = redirect_to_next_auth_step()
    return jsonify({"success": True, "redirect": redirect_response.location})


@bp.route("/auth/fido2-setup", methods=("GET", "POST"))
@csrf.exempt
def setup():
    """Register a new WebAuthn credential during authentication flow."""
    if not current_app.features.has_fido:
        abort(404)

    if not g.auth and g.get("session"):
        session["redirect-after-login"] = url_for(
            "core.account.profile_settings", edited_user=g.session.user
        )
        g.auth = AuthenticationSession(
            user_name=g.session.user.user_name,
            welcome_flash=False,
            remaining=["fido2"],
        )
        g.auth.save()

    if request.method == "GET":
        return generate_registration_options_view()

    return verify_registration_response_view()


def generate_registration_options_view():
    """Generate WebAuthn registration options."""
    if not g.auth.user:
        abort(400)

    max_credentials = current_app.config["CANAILLE"]["FIDO_MAX_CREDENTIALS"]
    if len(g.auth.user.webauthn_credentials) >= max_credentials:
        flash(
            _(
                "Maximum number of security keys reached ({max}). Please remove one before adding another."
            ).format(max=max_credentials),
            "error",
        )
        return redirect(
            url_for("core.account.profile_settings", edited_user=g.auth.user)
        )

    rp_id = get_rp_id()
    rp_name = get_rp_name()

    exclude_credentials = []
    for credential in g.auth.user.webauthn_credentials:
        transports = (
            deserialize_transports(credential.transports)
            if credential.transports
            else None
        )
        descriptor = PublicKeyCredentialDescriptor(
            id=credential.credential_id, transports=transports
        )
        exclude_credentials.append(descriptor)

    timeout_ms = int(
        current_app.config["CANAILLE"]["FIDO_TIMEOUT"].total_seconds() * 1000
    )
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_id=g.auth.user.id.encode("utf-8"),
        user_name=g.auth.user.user_name,
        user_display_name=g.auth.user.display_name or g.auth.user.user_name,
        timeout=timeout_ms,
        attestation=AttestationConveyancePreference(
            current_app.config["CANAILLE"]["FIDO_ATTESTATION"]
        ),
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement(
                current_app.config["CANAILLE"]["FIDO_USER_VERIFICATION"]
            )
        ),
        exclude_credentials=exclude_credentials if exclude_credentials else None,
    )

    g.auth.data["fido_challenge"] = bytes_to_base64url(options.challenge)
    g.auth.save()

    return render_template(
        "core/auth/fido-setup.html",
        options_json=options_to_json(options),
    )


def verify_registration_response_view():
    """Verify WebAuthn registration response and create credential."""
    challenge = g.auth.data.get("fido_challenge")

    if not challenge or not g.auth.user:
        return jsonify({"success": False, "error": "Invalid session"}), 400

    max_credentials = current_app.config["CANAILLE"]["FIDO_MAX_CREDENTIALS"]
    if len(g.auth.user.webauthn_credentials) >= max_credentials:
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Maximum number of security keys reached ({max_credentials})",
                }
            ),
            400,
        )

    credential_data = request.get_json()
    if not credential_data:
        return jsonify({"success": False, "error": "Invalid JSON"}), 400

    credential_response = credential_data.get("credential")
    if not credential_response:
        return jsonify({"success": False, "error": "Missing credential data"}), 400

    try:
        verification = verify_registration_response(
            credential=credential_response,
            expected_challenge=base64url_to_bytes(challenge),
            expected_origin=get_origin(),
            expected_rp_id=get_rp_id(),
            require_user_verification=current_app.config["CANAILLE"][
                "FIDO_USER_VERIFICATION"
            ]
            == "required",
        )
    except InvalidRegistrationResponse as e:
        current_app.logger.security(
            f"Failed WebAuthn registration for {g.auth.user_name}: {e}"
        )
        return jsonify({"success": False, "error": str(e)}), 400

    credential = models.WebAuthnCredential()
    credential.credential_id = verification.credential_id
    credential.public_key = verification.credential_public_key
    credential.sign_count = verification.sign_count
    aaguid = verification.aaguid
    if aaguid is not None:
        if isinstance(aaguid, str):
            aaguid = uuid.UUID(aaguid).bytes
        elif hasattr(aaguid, "bytes"):
            aaguid = aaguid.bytes
    credential.aaguid = aaguid
    credential.transports = serialize_transports(
        credential_response.get("response", {}).get("transports", [])
    )
    credential.name = _("My security key")
    credential.created_at = datetime.datetime.now(datetime.timezone.utc)
    credential.user = g.auth.user

    Backend.instance.save(credential)

    current_app.logger.security(
        f"WebAuthn credential registered for {g.auth.user_name}"
    )
    flash(_("Security key successfully registered."), "success")

    if g.get("session"):
        g.auth = None
        session.pop("auth", None)
        redirect_url = url_for(
            "core.account.profile_settings", edited_user=g.session.user
        )
    else:
        g.auth.set_step_finished("fido2")
        redirect_response = redirect_to_next_auth_step()
        redirect_url = redirect_response.location

    return jsonify({"success": True, "redirect": redirect_url})
