import datetime
import uuid

from authlib.common.urls import add_params_to_uri
from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749.errors import InvalidRequestError
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
from ..utils import SCOPE_DETAILS
from .forms import AuthorizeForm
from .well_known import openid_configuration

bp = Blueprint("endpoints", __name__, url_prefix="/oauth")

AUTHORIZATION_REQUEST_PROCESS_TIMEOUT: int = 300


@bp.errorhandler(HTTPException)
def http_error_handler(error):
    return {
        "error": error.name.lower().replace(" ", "_"),
        "error_description": error.description,
    }, error.code


@bp.errorhandler(Exception)
def internal_error_handler(error):
    return {
        "error": "internal_server_error",
        "error_description": str(error),
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
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    current_app.logger.debug(
        "authorization endpoint request:\nGET: %s\nPOST: %s",
        request.args.to_dict(flat=False),
        request.form.to_dict(flat=False),
    )

    redirect_url = (
        request.url
        if request.method == "GET"
        else add_params_to_uri(request.url, request.form)
    )

    try:
        check_prompt_value()

        ui_locales = request.values.get("ui_locales")

        if response := authorize_login(redirect_url, now, ui_locales):
            return response

        return authorize_consent(redirect_url, now)

    except OAuth2Error as error:
        if not error.redirect_uri:
            return render_template(
                "error.html",
                description=error.get_error_description(),
                error_code=error.status_code,
            ), error.status_code

        return authorization.handle_error_response(request, error)


def check_prompt_value():
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
    if (
        request.values.get("prompt")
        and request.values["prompt"]
        not in openid_configuration()["prompt_values_supported"]
    ):
        raise InvalidRequestError(
            description=f"prompt '{request.values['prompt']}' value is not supported",
            redirect_uri=request.values.get("redirect_uri"),
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


def authorize_login(redirect_url, now, ui_locales):
    """If user authentication or registration is needed, return a redirection to the correct page."""
    save_authorization_request_datetime(redirect_url, now)

    if user := g.session and g.session.user:
        auth_time = g.session.last_login_datetime

        if request.values.get(
            "prompt"
        ) == "select_account" and auth_time < get_authorization_request_datetime(
            redirect_url
        ):
            session["redirect-after-login"] = redirect_url

            start_oidc_auth_session(
                client_id=request.values.get("client_id"),
                prompt=request.values.get("prompt"),
                ui_locales=ui_locales,
            )
            return redirect(url_for("core.auth.login"))

        if request.values.get(
            "prompt"
        ) == "login" and auth_time < get_authorization_request_datetime(redirect_url):
            session["redirect-after-login"] = redirect_url

            start_oidc_auth_session(
                client_id=request.values.get("client_id"),
                username=g.session.user.user_name,
                prompt=request.values.get("prompt"),
                ui_locales=ui_locales,
            )
            return redirect_to_next_auth_step()

        # hotfix for
        # https://github.com/lepture/authlib/issues/741
        max_age = auth_time + datetime.timedelta(
            seconds=int(request.values.get("max_age", 0))
        )
        if request.values.get("max_age") and max_age < now:
            session["redirect-after-login"] = redirect_url

            start_oidc_auth_session(
                client_id=request.values.get("client_id"),
                username=g.session.user.user_name,
                prompt=request.values.get("prompt"),
                ui_locales=ui_locales,
            )
            return redirect_to_next_auth_step()

        if not user.can_use_oidc:
            abort(
                403,
                "The user does not have the permission to achieve OIDC authentication.",
            )

    else:
        if request.values.get("prompt") == "create":
            session["redirect-after-login"] = redirect_url
            return redirect(url_for("core.account.join"))

        if request.values.get("prompt") != "none":
            session["redirect-after-login"] = redirect_url

            start_oidc_auth_session(
                client_id=request.values.get("client_id"),
                prompt=request.values.get("prompt"),
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
        request.values.get("prompt") == "consent"
        and consent
        and consent.issue_date < get_authorization_request_datetime(redirect_url)
    ):
        return True

    if grant.client.trusted:
        return False

    requested_scopes = request.values.get("scope", "")
    allowed_scopes = grant.client.get_allowed_scope(requested_scopes).split(" ")
    if consent and all(scope in set(consent.scope) for scope in allowed_scopes):
        return False

    return True


def create_or_update_consent(grant, user, now):
    consents = Backend.instance.query(
        models.Consent,
        client=grant.client,
        subject=user,
    )
    consent = consents[0] if consents else None

    requested_scopes = request.values.get("scope", "")
    allowed_scopes = grant.client.get_allowed_scope(requested_scopes).split(" ")

    if consent:
        if consent.revoked:
            consent.restore()
        consent.issue_date = now
        consent.scope = grant.client.get_allowed_scope(
            " ".join(set(allowed_scopes + consents[0].scope))
        ).split(" ")
    else:
        consent = models.Consent(
            consent_id=str(uuid.uuid4()),
            client=grant.client,
            subject=user,
            scope=allowed_scopes,
            issue_date=now,
        )
    Backend.instance.save(consent)
    current_app.logger.security(
        f"New consent for {user.user_name} in client {consent.client.client_name}"
    )


def authorize_consent(redirect_url, now):
    user = g.session and g.session.user
    grant = authorization.get_consent_grant(end_user=user)

    # Get the authorization code, or display the user consent form
    if request.method == "GET" or "answer" not in request.form:
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
        elif request.values.get("prompt") == "none":
            raise ConsentRequiredError(redirect_uri=request.values["redirect_uri"])

        form = AuthorizeForm(request.form or None)
        form.action = redirect_url
        requested_scope = request.values.get("scope")
        effective_scope = grant.client.get_allowed_scope(requested_scope)
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

    if request.form["answer"] == "logout":
        session["redirect-after-login"] = redirect_url
        start_oidc_auth_session(
            client_id=request.values.get("client_id"),
            prompt=request.values.get("prompt"),
            ui_locales=request.values.get("ui_locales"),
        )
        return redirect(url_for("core.auth.logout"))

    if request.form["answer"] == "deny":
        grant_user = None

    if request.form["answer"] == "accept":
        grant_user = user
        create_or_update_consent(grant, grant_user, now)

    response = authorization.create_authorization_response(
        grant=grant, grant_user=grant_user
    )

    current_app.logger.debug("authorization endpoint response: %s", response.location)
    return response


@bp.route("/token", methods=["POST"])
@csrf.exempt
def issue_token():
    request_params = request.form.to_dict(flat=False)
    grant_type = (
        request_params["grant_type"][0] if request_params["grant_type"] else None
    )
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


@bp.route("/introspect", methods=["POST"])
@csrf.exempt
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
def revoke_token():
    current_app.logger.debug(
        "revokation endpoint request: POST: %s", request.form.to_dict(flat=False)
    )
    response = authorization.create_endpoint_response(RevocationEndpoint.ENDPOINT_NAME)
    current_app.logger.debug("revokation endpoint response: %s", response.json)
    return response


@bp.route("/register", methods=["POST"])
@csrf.exempt
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
def jwks():
    jwks = server_jwks()
    return jsonify(jwks.as_dict(private=False))


@bp.route("/userinfo", methods=["GET", "POST"])
@csrf.exempt
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

    needs_confirmation = (
        req.logout_hint and g.user and req.logout_hint != g.user.user_name
    )
    if request.method == "GET" and req.needs_confirmation or needs_confirmation:
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

        if request.form.get("answer") != "logout":
            flash(_("You have not been disconnected"), "info")
            return redirect(url_for("core.account.index"))

    # redirect to the client post_logout_redirect_uri
    if response := authorization.create_endpoint_response(
        EndSessionEndpoint.ENDPOINT_NAME, req
    ):
        current_app.logger.debug("end_session endpoint response: %s", response)
        return response

    # display local logout page
    flash(_("You have been disconnected"), "success")
    return redirect(url_for("core.account.index"))
