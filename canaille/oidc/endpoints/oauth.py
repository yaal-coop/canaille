import datetime
import uuid

from authlib.common.urls import add_params_to_uri
from authlib.integrations.flask_oauth2 import current_token
from authlib.jose import jwt
from authlib.jose.errors import JoseError
from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749.errors import InvalidRequestError
from authlib.oidc.core.errors import ConsentRequiredError
from flask import Blueprint
from flask import abort
from flask import current_app
from flask import flash
from flask import jsonify
from flask import redirect
from flask import request
from flask import session
from flask import url_for
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.exceptions import HTTPException

from canaille.app import models
from canaille.app.flask import cache
from canaille.app.flask import csrf
from canaille.app.i18n import gettext as _
from canaille.app.session import current_user
from canaille.app.session import current_user_login_datetime
from canaille.app.session import logout_user
from canaille.app.templating import render_template
from canaille.backends import Backend

from ..oauth import ClientConfigurationEndpoint
from ..oauth import ClientRegistrationEndpoint
from ..oauth import IntrospectionEndpoint
from ..oauth import RevocationEndpoint
from ..oauth import authorization
from ..oauth import generate_user_info
from ..oauth import get_issuer
from ..oauth import get_public_jwks
from ..oauth import require_oauth
from ..utils import SCOPE_DETAILS
from .forms import AuthorizeForm
from .forms import LogoutForm
from .well_known import openid_configuration

bp = Blueprint("endpoints", __name__, url_prefix="/oauth")

AUTHORIZATION_REQUEST_PROCESS_TIMEOUT: int = 300


@bp.errorhandler(HTTPException)
def http_error_handler(error):
    return {
        "error": error.name.lower().replace(" ", "_"),
        "error_description": error.description,
    }, error.code


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
        # Check that the request is well-formed
        check_prompt_value()

        # Check that login is needed
        if response := authorize_login(redirect_url, now):
            return response

        # Get the user consent if needed
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


def authorize_login(redirect_url, now):
    """If user authentication or registration is needed, return a redirection to the correct page."""
    save_authorization_request_datetime(redirect_url, now)
    user = current_user()

    if not user:
        if request.values.get("prompt") == "create":
            session["redirect-after-login"] = redirect_url
            return redirect(url_for("core.account.join"))

        if request.values.get("prompt") != "none":
            session["redirect-after-login"] = redirect_url
            return redirect(url_for("core.auth.login"))

    else:
        auth_time = current_user_login_datetime()
        if request.values.get(
            "prompt"
        ) == "login" and auth_time < get_authorization_request_datetime(redirect_url):
            session["redirect-after-login"] = redirect_url
            return redirect(url_for("core.auth.password"))

        # https://github.com/lepture/authlib/issues/741
        max_age = auth_time + datetime.timedelta(
            seconds=int(request.values.get("max_age", 0))
        )
        if request.values.get("max_age") and max_age < now:
            session["redirect-after-login"] = redirect_url
            return redirect(url_for("core.auth.password"))

        if not user.can_use_oidc:
            abort(
                403,
                "The user does not have the permission to achieve OIDC authentication.",
            )


def is_consent_needed(grant, redirect_url) -> bool:
    """Check whether the consent page must be displayed."""
    consents = Backend.instance.query(
        models.Consent,
        client=grant.client,
        subject=current_user(),
    )
    consent = consents[0] if consents else None

    if consent and consent.revoked:
        return True

    if request.values.get(
        "prompt"
    ) == "consent" and consent.issue_date < get_authorization_request_datetime(
        redirect_url
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
    user = current_user()
    grant = authorization.get_consent_grant(end_user=user)

    # Get the authorization code, or display the user consent form
    if request.method == "GET" or "answer" not in request.form:
        if not is_consent_needed(grant, redirect_url):
            return authorization.create_authorization_response(grant_user=user)

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
        return render_template(
            "oidc/authorize.html",
            user=user,
            grant=grant,
            client=grant.client,
            menu=False,
            scope_details=SCOPE_DETAILS,
            ignored_scopes=["openid"],
            form=form,
        )

    if request.form["answer"] == "logout":
        session["redirect-after-login"] = redirect_url
        return redirect(url_for("core.auth.logout"))

    if request.form["answer"] == "deny":
        grant_user = None

    if request.form["answer"] == "accept":
        grant_user = user
        create_or_update_consent(grant, grant_user, now)

    response = authorization.create_authorization_response(grant_user=grant_user)

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
    return jsonify(get_public_jwks())


@bp.route("/userinfo", methods=["GET", "POST"])
@require_oauth(["profile", "openid"])
@csrf.exempt
def userinfo():
    current_app.logger.debug("userinfo endpoint request: %s", request.args)
    response = generate_user_info(current_token.subject, current_token.scope)
    current_app.logger.debug("userinfo endpoint response: %s", response)
    return jsonify(response)


@bp.route("/end_session", methods=["GET", "POST"])
@csrf.exempt
def end_session():
    data = CombinedMultiDict((request.args, request.form))
    user = current_user()

    if not user:
        return redirect(url_for("core.account.index"))

    form = LogoutForm(request.form)
    form.action = url_for("oidc.endpoints.end_session_submit")

    client = None
    valid_uris = []

    if "client_id" in data:
        client = Backend.instance.get(models.Client, client_id=data["client_id"])
        if client:
            valid_uris = client.post_logout_redirect_uris

    if (
        not data.get("id_token_hint")
        or (data.get("logout_hint") and data["logout_hint"] != user.user_name)
    ) and not session.get("end_session_confirmation"):
        session["end_session_data"] = data
        return render_template("oidc/logout.html", form=form, client=client, menu=False)

    if data.get("id_token_hint"):
        try:
            id_token = jwt.decode(
                data["id_token_hint"],
                current_app.config["CANAILLE_OIDC"]["JWT"]["PUBLIC_KEY"],
            )
        except JoseError as exc:
            return jsonify(
                {
                    "status": "error",
                    "message": str(exc),
                }
            )

        if not id_token["iss"] == get_issuer():
            return jsonify(
                {
                    "status": "error",
                    "message": "id_token_hint has not been issued here",
                }
            )

        if "client_id" in data:
            if (
                data["client_id"] != id_token["aud"]
                and data["client_id"] not in id_token["aud"]
            ):
                return jsonify(
                    {
                        "status": "error",
                        "message": "id_token audience and client_id don't match",
                    }
                )

        else:
            client_ids = (
                id_token["aud"]
                if isinstance(id_token["aud"], list)
                else [id_token["aud"]]
            )
            for client_id in client_ids:
                client = Backend.instance.get(models.Client, client_id=client_id)
                if client:
                    valid_uris.extend(client.post_logout_redirect_uris or [])

        if user.user_name != id_token["sub"] and not session.get(
            "end_session_confirmation"
        ):
            session["end_session_data"] = data
            return render_template(
                "oidc/logout.html", form=form, client=client, menu=False
            )

    logout_user()

    if "end_session_confirmation" in session:
        del session["end_session_confirmation"]

    if (
        "post_logout_redirect_uri" in data
        and data["post_logout_redirect_uri"] in valid_uris
    ):
        url = data["post_logout_redirect_uri"]
        if "state" in data:
            url = add_params_to_uri(url, dict(state=data["state"]))
        return redirect(url)

    flash(_("You have been disconnected"), "success")
    return redirect(url_for("core.account.index"))


@bp.route("/end_session_confirm", methods=["POST"])
@csrf.exempt
def end_session_submit():
    form = LogoutForm(request.form)
    form.validate()

    data = session["end_session_data"]
    del session["end_session_data"]

    if request.form["answer"] == "logout":
        session["end_session_confirmation"] = True
        url = add_params_to_uri(url_for("oidc.endpoints.end_session"), data)
        return redirect(url)

    flash(_("You have not been disconnected"), "info")

    return redirect(url_for("core.account.index"))
