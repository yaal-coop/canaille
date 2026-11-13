import datetime
import uuid

from authlib.common.urls import add_params_to_uri
from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc8628 import DEVICE_CODE_GRANT_TYPE
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
from werkzeug.exceptions import HTTPException

from canaille.app import models
from canaille.app.flask import any_host
from canaille.app.flask import csrf
from canaille.app.i18n import gettext as _
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.auth import AuthenticationSession
from canaille.core.auth import redirect_to_next_auth_step
from canaille.oidc.endpoints.forms import LogoutForm

from ..jose import server_jwks
from ..provider import AuthorizationSession
from ..provider import ClientConfigurationEndpoint
from ..provider import ClientRegistrationEndpoint
from ..provider import EndSessionEndpoint
from ..provider import IntrospectionEndpoint
from ..provider import RevocationEndpoint
from ..provider import UserInfoEndpoint
from ..provider import authorization
from ..provider import get_consent
from ..userinfo import generate_user_claims
from ..utils import SCOPE_DETAILS
from ..utils import unique_scopes
from .forms import AuthorizeForm
from .forms import DeviceForm

bp = Blueprint("endpoints", __name__, url_prefix="/oauth")


@bp.errorhandler(HTTPException)
def http_error_handler(error):
    return {
        "error": error.name.lower().replace(" ", "_"),
        "error_description": error.description,
    }, error.code


@bp.errorhandler(Exception)
def internal_error_handler(error):
    current_app.logger.exception(error)
    return {
        "error": "internal_server_error",
        "error_description": "The server encountered an unexpected error.",
    }, 500


@bp.before_request
def extract_ui_locales():
    """Extract OIDC ui_locales parameter for locale selection."""
    if ui_locales := request.values.get("ui_locales"):
        g.ui_locales = ui_locales


@bp.route("/authorize", methods=["GET", "POST"])
@csrf.exempt
def authorize():
    now = datetime.datetime.now(tz=datetime.UTC)
    current_app.logger.debug(
        "authorization endpoint request:\nGET: %s\nPOST: %s",
        request.args.to_dict(flat=False),
        request.form.to_dict(flat=False),
    )

    # Authorization requests sent with POST come from the client website, so
    # the browser does not send the SameSite session cookie with them. They are
    # turned into GET requests, that the browser sends with the cookie.
    if request.method == "POST" and "answer" not in request.form:
        return redirect(add_params_to_uri(request.url, request.form), code=303)

    # The consent form posts its answer to the URL of the authorization request.
    redirect_url = request.url

    user = g.session.user if g.session else None
    authorization_session = AuthorizationSession(user, session)
    try:
        grant = authorization.get_consent_grant(session=authorization_session)
    except OAuth2Error as error:
        if not error.redirect_uri:
            return render_template(
                "error.html",
                description=error.get_error_description(),
                error_code=error.status_code,
            ), error.status_code

        return authorization.handle_error_response(request, error)

    g.ui_locales = grant.request.payload.data.get("ui_locales")
    try:
        # Users who are asked to select an account can switch to another one
        # first, so they are checked once the account is selected.
        if "select_account" not in grant.interactions:
            check_client_usability(grant)

        if response := authorize_interactions(grant, redirect_url):
            return response

        return authorize_consent(grant, redirect_url, now)

    except Exception:
        authorization_session.end_request(grant.request)
        raise


def check_client_usability(grant):
    """Refuse the logged users who cannot use the client."""
    user = grant.request.user
    if user and not grant.client.is_usable_by(user):
        abort(403, "The user cannot use this client.")


def start_oidc_auth_session(
    client_id, username=None, prompt_login=False, ui_locales=None
):
    """Create and save an AuthenticationSession for OIDC authentication.

    With ``prompt_login``, the login page tells logged users that the client
    asks them to log in again.
    """
    g.auth = AuthenticationSession(
        user_name=username,
        data={
            "prompt_login": prompt_login,
            "client_id": client_id,
        },
        template="oidc/auth.html",
        ui_locales=ui_locales,
    )
    g.auth.save()


def authorize_interactions(grant, redirect_url):
    """Return a redirection to the registration or login page, when the user must go through it.

    Anonymous users and users who must select an account get the login page.
    Logged users who must log in again get the next authentication step.
    """
    params = grant.request.payload.data
    user = grant.request.user
    interactions = grant.interactions

    if "create" in interactions:
        session["redirect-after-login"] = redirect_url
        return redirect(url_for("core.account.join"))

    if "select_account" in interactions or ("login" in interactions and not user):
        session["redirect-after-login"] = redirect_url
        start_oidc_auth_session(
            client_id=grant.client.client_id,
            prompt_login=bool(user) and "login" in interactions,
            ui_locales=params.get("ui_locales"),
        )
        return redirect(url_for("core.auth.login"))

    if "login" in interactions:
        session["redirect-after-login"] = redirect_url
        start_oidc_auth_session(
            client_id=grant.client.client_id,
            username=user.user_name,
            prompt_login=True,
            ui_locales=params.get("ui_locales"),
        )
        return redirect_to_next_auth_step()

    return None


def create_or_update_consent(client, user, scope, now):
    consent = get_consent(client, user)
    allowed_scopes = unique_scopes(client.get_allowed_scope(scope))

    if consent:
        if consent.revoked:
            consent.restore()
        consent.issue_date = now
        consent.scope = client.get_allowed_scope(
            " ".join(set(allowed_scopes + consent.scope))
        ).split(" ")
    else:
        consent = models.Consent(
            consent_id=str(uuid.uuid4()),
            client=client,
            subject=user,
            scope=allowed_scopes,
            issue_date=now,
        )
    Backend.instance.save(consent)
    current_app.logger.security(
        f"New consent for {user.user_name} in client {consent.client.client_name}"
    )


def authorize_consent(grant, redirect_url, now):
    user = grant.request.user
    params = grant.request.payload.data
    effective_scope = grant.client.get_allowed_scope(grant.request.payload.scope)

    # The answers without a valid CSRF token are ignored, as the authorization
    # endpoint itself is exempt from CSRF checks. The token is bound to the
    # user and the scope of the consent page, so another user of the session
    # cannot accept it, and a request_uri cannot change the scope after the
    # page is displayed.
    form = AuthorizeForm(
        request.form or None,
        meta={
            "csrf_bind": f"{user.id if user else ''} {redirect_url} {effective_scope}"
        },
    )
    answered = (
        request.method == "POST" and form.answer.data is not None and form.validate()
    )

    # Get the authorization code, or display the user consent form.
    if not answered:
        if "consent" not in grant.interactions:
            response = authorization.create_authorization_response(
                grant=grant, grant_user=user
            )
            current_app.logger.debug(
                "authorization endpoint response (trusted): %s",
                response.location or response.get_data(as_text=True),
            )
            return response

        form.action_url = redirect_url
        return render_template(
            "oidc/authorize.html",
            user=user,
            grant=grant,
            client=grant.client,
            menu=False,
            scope_details=SCOPE_DETAILS,
            ignored_scopes=["openid"],
            form=form,
            effective_scope=effective_scope,
        )

    if form.answer.data not in ("accept", "deny", "logout"):
        abort(400, "Unknown consent answer.")

    if form.answer.data == "logout":
        session["redirect-after-login"] = redirect_url
        start_oidc_auth_session(
            client_id=params.get("client_id"),
            ui_locales=params.get("ui_locales"),
        )
        return redirect(url_for("core.auth.logout"))

    if form.answer.data == "deny":
        grant_user = None

    if form.answer.data == "accept":
        grant_user = user
        create_or_update_consent(
            grant.client, grant_user, grant.request.payload.scope or "", now
        )

    response = authorization.create_authorization_response(
        grant=grant, grant_user=grant_user
    )

    current_app.logger.debug(
        "authorization endpoint response: %s",
        response.location or response.get_data(as_text=True),
    )
    return response


@bp.route("/token", methods=["POST"])
@csrf.exempt
@any_host
def issue_token():
    request_params = request.form.to_dict(flat=False)
    grant_type = request.form.get("grant_type")
    current_app.logger.debug("token endpoint request: POST: %s", request_params)
    response = authorization.create_token_response()
    current_app.logger.debug("token endpoint response: %s", response.json)

    if response.json.get("access_token"):
        access_token = response.json["access_token"]
        token = Backend.instance.get(models.Token, access_token=access_token)
        if token.subject:
            current_app.logger.security(
                f"Issued {grant_type} token for {token.subject.user_name} in client {token.client.client_name}"
            )
        else:
            current_app.logger.security(
                f"Issued {grant_type} token for client {token.client.client_name}"
            )

    return response


@bp.route("/device_authorization", methods=["POST"])
@csrf.exempt
@any_host
def device_authorization():
    """Issue a device code and user code for a device authorization request (RFC 8628)."""
    current_app.logger.debug(
        "device authorization endpoint request: POST: %s",
        request.form.to_dict(flat=False),
    )
    return authorization.create_endpoint_response("device_authorization")


def normalize_user_code(raw: str) -> str:
    """Normalize a user-submitted user_code.

    Per RFC 8628 section 6.1, the server strips punctuation it added for
    readability, uppercases the input and re-groups it with dashes so that the
    dashes are optional for the user.
    """
    user_code_type = current_app.config["CANAILLE_OIDC"]["DEVICE_USER_CODE_TYPE"]
    cleaned = "".join(char for char in raw.upper() if char.isalnum())
    size = 3 if user_code_type == "digital" else 4
    groups = [cleaned[i : i + size] for i in range(0, len(cleaned), size)]
    return "-".join(groups)


def get_active_device_code(raw_user_code: str):
    """Return a pending, non-expired device code matching the given user code.

    The client must still be allowed to use the device authorization grant.
    """
    canonical = normalize_user_code(raw_user_code)
    codes = Backend.instance.query(models.DeviceCode, user_code=canonical)
    return next(
        (
            code
            for code in codes
            if code.status == "pending"
            and not code.is_expired()
            and code.client.check_grant_type(DEVICE_CODE_GRANT_TYPE)
        ),
        None,
    )


@bp.route("/device", methods=["GET", "POST"])
def device():
    """Device verification page (RFC 8628).

    The user enters (or confirms) the ``user_code`` displayed on the device,
    then approves or denies the authorization request.
    """
    now = datetime.datetime.now(tz=datetime.UTC)
    user = g.session and g.session.user
    if not user:
        session["redirect-after-login"] = request.url
        return redirect(url_for("core.auth.login"))

    if not user.can_use_oidc:
        abort(
            403,
            "The user does not have the permission to achieve OIDC authentication.",
        )

    if request.method == "POST" and "answer" in request.form:
        if request.form["answer"] not in ("accept", "deny"):
            abort(400, "Unknown consent answer.")

        device_code = get_active_device_code(request.form.get("user_code", ""))
        if device_code is None:
            flash(_("The user code is invalid or has expired."), "error")
            return render_template("oidc/device.html", form=DeviceForm(), menu=False)

        if not device_code.client.is_usable_by(user):
            abort(403, "The user cannot use this client.")

        device_code.subject = user
        granted = request.form["answer"] == "accept"
        device_code.status = "authorized" if granted else "denied"
        Backend.instance.save(device_code)
        if granted:
            create_or_update_consent(
                device_code.client, user, " ".join(device_code.scope), now
            )
        current_app.logger.security(
            f"Device authorization {'granted' if granted else 'denied'} "
            f"by {user.user_name} for client {device_code.client.client_name}"
        )
        return render_template(
            "oidc/device.html",
            form=DeviceForm(),
            menu=False,
            confirmed=True,
            granted=granted,
            client=device_code.client,
        )

    form = DeviceForm(
        request.form or None,
        data={"user_code": request.args.get("user_code", "")},
    )

    if not form.validate_on_submit() and not request.args.get("user_code"):
        return render_template("oidc/device.html", form=form, menu=False)

    device_code = get_active_device_code(form.user_code.data)
    if device_code is None:
        flash(_("The user code is invalid or has expired."), "error")
        return render_template("oidc/device.html", form=form, menu=False)

    if not device_code.client.is_usable_by(user):
        abort(403, "The user cannot use this client.")

    return render_template(
        "oidc/device.html",
        form=form,
        menu=False,
        user=user,
        device_code=device_code,
        client=device_code.client,
        scope_details=SCOPE_DETAILS,
        ignored_scopes=["openid"],
        effective_scope=device_code.client.get_allowed_scope(
            " ".join(device_code.scope)
        ),
    )


@bp.route("/introspect", methods=["POST"])
@csrf.exempt
@any_host
def introspect_token():
    current_app.logger.debug(
        "introspection endpoint request: POST: %s", request.form.to_dict(flat=False)
    )
    response = authorization.create_endpoint_response(
        IntrospectionEndpoint.ENDPOINT_NAME
    )
    current_app.logger.debug("introspection endpoint response: %s", response.json)
    return response


@bp.route("/revoke", methods=["POST"])
@csrf.exempt
@any_host
def revoke_token():
    current_app.logger.debug(
        "revokation endpoint request: POST: %s", request.form.to_dict(flat=False)
    )
    response = authorization.create_endpoint_response(RevocationEndpoint.ENDPOINT_NAME)
    current_app.logger.debug("revokation endpoint response: %s", response.json)
    return response


@bp.route("/register", methods=["POST"])
@csrf.exempt
@any_host
def client_registration():
    current_app.logger.debug(
        "client registration endpoint request: POST: %s",
        request.json,
    )

    response = authorization.create_endpoint_response(
        ClientRegistrationEndpoint.ENDPOINT_NAME
    )
    current_app.logger.debug("client registration endpoint response: %s", response.json)
    return response


@bp.route("/register/<client_id>", methods=["GET", "PUT", "DELETE"])
@csrf.exempt
@any_host
def client_registration_management(client_id):
    if request.method == "PUT":
        current_app.logger.debug(
            "client registration management endpoint request: PUT: %s",
            request.json,
        )
    response = authorization.create_endpoint_response(
        ClientConfigurationEndpoint.ENDPOINT_NAME
    )
    current_app.logger.debug(
        "client registration management endpoint response: %s", response.json
    )
    return response


@bp.route("/jwks.json")
@any_host
def jwks():
    jwks = server_jwks()
    return jsonify(jwks.as_dict(private=False))


@bp.route("/userinfo", methods=["GET", "POST"])
@csrf.exempt
@any_host
def userinfo():
    current_app.logger.debug("userinfo endpoint request: %s", request.args)
    response = authorization.create_endpoint_response(UserInfoEndpoint.ENDPOINT_NAME)
    current_app.logger.debug("userinfo endpoint response: %s", response)
    return response


@bp.route("/end_session", methods=["GET", "POST"])
@csrf.exempt
def end_session():
    current_app.logger.debug("end_session endpoint request: %s", request.args)
    try:
        req = authorization.validate_endpoint_request(EndSessionEndpoint.ENDPOINT_NAME)
    except OAuth2Error as error:
        return authorization.handle_error_response(None, error)

    current_user = g.session and g.session.user

    # Client owners choose the post-logout redirection URIs, so users only get
    # redirected there after they confirm the logout.
    owned_client = req.client and req.client.owners
    if owned_client and not current_user:
        flash(_("You have been disconnected"), "success")
        return redirect(url_for("core.account.index"))

    needs_confirmation = current_user and (
        owned_client
        or (req.logout_hint and req.logout_hint != current_user.user_name)
        or (
            req.id_token_claims
            and req.id_token_claims.get("sub")
            != generate_user_claims(current_user).get("sub")
        )
    )
    if request.method == "GET" and (req.needs_confirmation or needs_confirmation):
        form = LogoutForm()
        return render_template(
            "oidc/logout.html", client=req.client, form=form, menu=False
        )

    if request.method == "POST":
        form = LogoutForm(request.form)
        if not form.validate():
            return render_template(
                "oidc/logout.html", client=req.client, form=form, menu=False
            )

        if form.answer.data != "logout":
            flash(_("You have not been disconnected"), "info")
            return redirect(url_for("core.account.index"))

    if response := authorization.create_endpoint_response(
        EndSessionEndpoint.ENDPOINT_NAME, req
    ):
        current_app.logger.debug("end_session endpoint response: %s", response)
        return response

    flash(_("You have been disconnected"), "success")
    return redirect(url_for("core.account.index"))
