import datetime
import uuid

from authlib.common.urls import add_params_to_uri
from authlib.integrations.flask_oauth2 import current_token
from authlib.jose import jwt
from authlib.jose.errors import JoseError
from authlib.oauth2 import OAuth2Error
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
from canaille.app.flask import csrf
from canaille.app.i18n import gettext as _
from canaille.app.session import current_user
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
from ..oauth import get_jwks
from ..oauth import require_oauth
from ..utils import SCOPE_DETAILS
from .forms import AuthorizeForm
from .forms import LogoutForm
from .well_known import openid_configuration

bp = Blueprint("endpoints", __name__, url_prefix="/oauth")


@bp.errorhandler(HTTPException)
def http_error_handler(error):
    return {
        "error": error.name.lower().replace(" ", "_"),
        "error_description": error.description,
    }, error.code


@bp.route("/authorize", methods=["GET", "POST"])
@csrf.exempt
def authorize():
    current_app.logger.debug(
        "authorization endpoint request:\nGET: %s\nPOST: %s",
        request.args.to_dict(flat=False),
        request.form.to_dict(flat=False),
    )

    data = CombinedMultiDict((request.args, request.form))
    client = Backend.instance.get(models.Client, client_id=data.get("client_id"))
    user = current_user()

    # Check that the request is well-formed
    if response := authorize_guards(client, data):
        return response

    # Check that the user is logged
    if response := authorize_login(user, data):
        return response

    # Get the user consent if needed
    response = authorize_consent(client, user, data)

    return response


def authorize_guards(client, data):
    if not data.get("client_id"):
        return {
            "error": "invalid_request",
            "error_description": "'client_id' parameter is missing.",
            "iss": get_issuer(),
        }, 400

    if not client:
        return {
            "error": "invalid_client",
            "error_description": "Invalid client.",
            "iss": get_issuer(),
        }, 400

    # https://openid.net/specs/openid-connect-prompt-create-1_0.html#name-authorization-request
    # If the OpenID Provider receives a prompt value that it does
    # not support (not declared in the prompt_values_supported
    # metadata field) the OP SHOULD respond with an HTTP 400 (Bad
    # Request) status code and an error value of invalid_request.
    # It is RECOMMENDED that the OP return an error_description
    # value identifying the invalid parameter value.
    # https://github.com/lepture/authlib/issues/735
    if (
        data.get("prompt")
        and data["prompt"] not in openid_configuration()["prompt_values_supported"]
    ):
        return {
            "error": "invalid_request",
            "error_description": f"prompt '{data['prompt']}' value is not supported",
            "iss": get_issuer(),
        }, 400

    # Ensures the request contains a redirect_uri until resolved upstream in Authlib
    # https://github.com/lepture/authlib/issues/712
    if not data.get("redirect_uri"):
        return {
            "error": "invalid_request",
            "error_description": "Missing 'redirect_uri' in request.",
            "iss": get_issuer(),
        }, 400


def authorize_login(user, data):
    if not user and data.get("prompt") != "none":
        session["redirect-after-login"] = request.url

        if data.get("prompt") == "create":
            return redirect(url_for("core.account.join"))

        return redirect(url_for("core.auth.login"))

    if user and not user.can_use_oidc:
        abort(
            403, "The user does not have the permission to achieve OIDC authentication."
        )


def authorize_consent(client, user, data):
    requested_scopes = data.get("scope", "").split(" ")
    allowed_scopes = client.get_allowed_scope(requested_scopes).split(" ")
    consents = Backend.instance.query(
        models.Consent,
        client=client,
        subject=user,
    )
    consent = consents[0] if consents else None

    # Get the authorization code, or display the user consent form
    if request.method == "GET" or "answer" not in request.form:
        try:
            grant = authorization.get_consent_grant(end_user=user)
        except OAuth2Error as error:
            current_app.logger.debug("authorization endpoint response: %s", error)
            return {**dict(error.get_body()), "iss": get_issuer()}, error.status_code

        client_has_user_consent = (
            (client.trusted and (not consent or not consent.revoked))
            or (
                consent and all(scope in set(consent.scope) for scope in allowed_scopes)
            )
            and not consent.revoked
        )
        if client_has_user_consent:
            return authorization.create_authorization_response(grant_user=user)

        # consent_required
        # The Authorization Server requires End-User consent.
        # This error MAY be returned when the prompt parameter value in the
        # Authentication Request is none, but the Authentication Request cannot
        # be completed without displaying a user interface for End-User consent.
        elif data.get("prompt") == "none":
            response = {
                "error": "consent_required",
                "iss": get_issuer(),
            }
            current_app.logger.debug("authorization endpoint response: %s", response)
            return response, 400

        form = AuthorizeForm(request.form or None)
        form.action = (
            request.url
            if request.method == "GET"
            else add_params_to_uri(request.url, data)
        )

        return render_template(
            "oidc/authorize.html",
            user=user,
            grant=grant,
            client=client,
            menu=False,
            scope_details=SCOPE_DETAILS,
            ignored_scopes=["openid"],
            form=form,
        )

    if request.form["answer"] == "logout":
        session["redirect-after-login"] = request.url
        return redirect(url_for("core.auth.logout"))

    if request.form["answer"] == "deny":
        grant_user = None

    if request.form["answer"] == "accept":
        grant_user = user

        if consent:
            if consent.revoked:
                consent.restore()
            consent.scope = client.get_allowed_scope(
                list(set(allowed_scopes + consents[0].scope))
            ).split(" ")
        else:
            consent = models.Consent(
                consent_id=str(uuid.uuid4()),
                client=client,
                subject=user,
                scope=allowed_scopes,
                issue_date=datetime.datetime.now(datetime.timezone.utc),
            )
        Backend.instance.save(consent)
        current_app.logger.security(
            f"New consent for {user.user_name} in client {consent.client.client_name}"
        )

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
    return jsonify(get_jwks())


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
