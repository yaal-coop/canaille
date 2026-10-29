import datetime
import uuid

from authlib.common.urls import add_params_to_uri
from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749.errors import InvalidRequestError
from authlib.oauth2.rfc6749.errors import UnsupportedResponseTypeError
from authlib.oauth2.rfc8628 import DEVICE_CODE_GRANT_TYPE
from authlib.oidc.core.errors import ConsentRequiredError
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
from canaille.app.flask import cache
from canaille.app.flask import csrf
from canaille.app.i18n import gettext as _
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.auth import AuthenticationSession
from canaille.core.auth import redirect_to_next_auth_step
from canaille.oidc.endpoints.forms import LogoutForm

from ..jose import server_jwks
from ..provider import ClientConfigurationEndpoint
from ..provider import ClientRegistrationEndpoint
from ..provider import EndSessionEndpoint
from ..provider import IntrospectionEndpoint
from ..provider import RevocationEndpoint
from ..provider import UserInfoEndpoint
from ..provider import authorization
from ..userinfo import generate_user_claims
from ..utils import SCOPE_DETAILS
from ..utils import unique_scopes
from .forms import AuthorizeForm
from .forms import DeviceForm
from .well_known import openid_configuration

bp = Blueprint("endpoints", __name__, url_prefix="/oauth")

AUTHORIZATION_REQUEST_PROCESS_TIMEOUT: int = 300


@bp.errorhandler(HTTPException)
def http_error_handler(error):
    return {
        "error": error.name.lower().replace(" ", "_"),
        "error_description": error.description,
    }, error.code


# Authlib lets InsecureTransportError escape from create_*_response:
# https://github.com/authlib/authlib/issues/973
@bp.errorhandler(OAuth2Error)
def oauth2_error_handler(error):
    current_app.logger.warning(
        "OAuth request refused on %s: %s: %s",
        request.url,
        error.error,
        error.get_error_description(),
    )
    return authorization.handle_error_response(request, error)


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


def save_authorization_request_datetime(request_url: str, now: datetime.datetime):
    key = f"auth-request:{request_url}"
    if not cache.get(key):
        cache.set(key, now.isoformat(), timeout=AUTHORIZATION_REQUEST_PROCESS_TIMEOUT)


def get_authorization_request_datetime(request_url: str) -> datetime.datetime | None:
    key = f"auth-request:{request_url}"
    return datetime.datetime.fromisoformat(cache.get(key)) if cache.get(key) else None


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

    try:
        params = authorization_parameters()
        check_client_usability(params)
        g.ui_locales = params.get("ui_locales")
        check_prompt_value(params)

        if response := authorize_login(redirect_url, now, params):
            return response

        return authorize_consent(redirect_url, now, params)

    except OAuth2Error as error:
        if not error.redirect_uri:
            return render_template(
                "error.html",
                description=error.get_error_description(),
                error_code=error.status_code,
            ), error.status_code

        return authorization.handle_error_response(request, error)


def check_client_usability(params):
    """Refuse the logged users who cannot use the client.

    This happens before any error redirection, as the client owners choose the
    redirection URIs. Users who are asked to select an account can switch to
    another one first.
    """
    if params.get("prompt") == "select_account":
        return

    user = g.session and g.session.user
    client = Backend.instance.get(models.Client, client_id=params.get("client_id"))
    if user and client and not client.is_usable_by(user):
        abort(403, "The user cannot use this client.")


def authorization_parameters():
    """Return the parameters of the authorization request.

    Per OIDC Core §6.1, the parameters of a request object replace the ones of the query.
    """
    oauth_request = authorization.create_oauth2_request(request)
    try:
        authorization.get_authorization_grant(oauth_request)
    except UnsupportedResponseTypeError:
        # This error redirects to the client. For logged users, it is raised
        # again by get_consent_grant, after the client usability checks.
        if not (g.session and g.session.user):
            raise
    return oauth_request.payload.data


def check_prompt_value(params):
    # Until this is fixed upstream:
    # https://github.com/lepture/authlib/issues/735
    #
    # https://openid.net/specs/openid-connect-prompt-create-1_0.html#name-authorization-request
    # If the OpenID Provider receives a prompt value that it does
    # not support (not declared in the prompt_values_supported
    # metadata field) the OP SHOULD respond with an HTTP 400 (Bad
    # Request) status code and an error value of invalid_request.
    # It is RECOMMENDED that the OP return an error_description
    # value identifying the invalid parameter value.
    prompt = params.get("prompt")
    if prompt and prompt not in openid_configuration()["prompt_values_supported"]:
        client = Backend.instance.get(models.Client, client_id=params.get("client_id"))
        redirect_uri = params.get("redirect_uri")
        raise InvalidRequestError(
            description=f"prompt '{prompt}' value is not supported",
            redirect_uri=redirect_uri
            if client and client.check_redirect_uri(redirect_uri)
            else None,
        )


def start_oidc_auth_session(client_id, username=None, prompt=None, ui_locales=None):
    """Create and save an AuthenticationSession for OIDC authentication."""
    g.auth = AuthenticationSession(
        user_name=username,
        data={
            "prompt_login": prompt == "login",
            "client_id": client_id,
        },
        template="oidc/auth.html",
        ui_locales=ui_locales,
    )
    g.auth.save()


def authorize_login(redirect_url, now, params):
    """If user authentication or registration is needed, return a redirection to the correct page."""
    save_authorization_request_datetime(redirect_url, now)
    request_time = get_authorization_request_datetime(redirect_url) or now
    prompt = params.get("prompt")
    client_id = params.get("client_id")
    ui_locales = params.get("ui_locales")

    if g.session and g.session.user:
        auth_time = g.session.last_login_datetime

        if prompt == "select_account" and auth_time < request_time:
            session["redirect-after-login"] = redirect_url

            start_oidc_auth_session(
                client_id=client_id,
                prompt=prompt,
                ui_locales=ui_locales,
            )
            return redirect(url_for("core.auth.login"))

        if prompt == "login" and auth_time < request_time:
            session["redirect-after-login"] = redirect_url

            start_oidc_auth_session(
                client_id=client_id,
                username=g.session.user.user_name,
                prompt=prompt,
                ui_locales=ui_locales,
            )
            return redirect_to_next_auth_step()

        # hotfix for
        # https://github.com/lepture/authlib/issues/741
        try:
            max_age_seconds = int(params.get("max_age") or 0)
        except ValueError:
            max_age_seconds = -1

        if max_age_seconds < 0:
            raise InvalidRequestError(
                description="The 'max_age' parameter must be a positive integer."
            )

        # The authentication age is measured at the authorization request time,
        # so the user is not asked to log in again after they just did.
        max_age = auth_time + datetime.timedelta(seconds=max_age_seconds)
        if params.get("max_age") not in (None, "") and max_age < request_time:
            session["redirect-after-login"] = redirect_url

            start_oidc_auth_session(
                client_id=client_id,
                username=g.session.user.user_name,
                prompt=prompt,
                ui_locales=ui_locales,
            )
            return redirect_to_next_auth_step()

    else:
        if prompt == "create":
            session["redirect-after-login"] = redirect_url
            return redirect(url_for("core.account.join"))

        if prompt != "none":
            session["redirect-after-login"] = redirect_url

            start_oidc_auth_session(
                client_id=client_id,
                prompt=prompt,
                ui_locales=ui_locales,
            )
            return redirect(url_for("core.auth.login"))


def is_consent_needed(grant, redirect_url) -> bool:
    """Check whether the consent page must be displayed."""
    consents = Backend.instance.query(
        models.Consent,
        client=grant.client,
        subject=g.session.user,
    )
    consent = consents[0] if consents else None

    if consent and consent.revoked:
        return True

    if (
        grant.request.payload.data.get("prompt") == "consent"
        and consent
        and consent.issue_date
        < (
            get_authorization_request_datetime(redirect_url)
            or datetime.datetime.now(tz=datetime.UTC)
        )
    ):
        return True

    if grant.client.trusted:
        return False

    requested_scopes = grant.request.payload.scope or ""
    allowed_scopes = unique_scopes(grant.client.get_allowed_scope(requested_scopes))
    if consent and all(scope in set(consent.scope) for scope in allowed_scopes):
        return False

    return True


def create_or_update_consent(client, user, scope, now):
    consents = Backend.instance.query(
        models.Consent,
        client=client,
        subject=user,
    )
    consent = consents[0] if consents else None

    allowed_scopes = unique_scopes(client.get_allowed_scope(scope))

    if consent:
        if consent.revoked:
            consent.restore()
        consent.issue_date = now
        consent.scope = client.get_allowed_scope(
            " ".join(set(allowed_scopes + consents[0].scope))
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


def authorize_consent(redirect_url, now, params):
    user = g.session and g.session.user
    client = Backend.instance.get(models.Client, client_id=params.get("client_id"))
    if user and client and not client.is_usable_by(user):
        abort(403, "The user cannot use this client.")

    grant = authorization.get_consent_grant(end_user=user)

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
        if not is_consent_needed(grant, redirect_url):
            response = authorization.create_authorization_response(
                grant=grant, grant_user=user
            )
            current_app.logger.debug(
                "authorization endpoint response (trusted): %s", response.location
            )
            return response

        # https://github.com/lepture/authlib/issues/740
        #
        # consent_required
        # The Authorization Server requires End-User consent.
        # This error MAY be returned when the prompt parameter value in the
        # Authentication Request is none, but the Authentication Request cannot
        # be completed without displaying a user interface for End-User consent.
        elif params.get("prompt") == "none":
            raise ConsentRequiredError(redirect_uri=grant.redirect_uri)

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
            prompt=params.get("prompt"),
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

    current_app.logger.debug("authorization endpoint response: %s", response.location)
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
