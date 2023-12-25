import datetime
import uuid

from authlib.integrations.flask_oauth2 import current_token
from authlib.jose import jwt
from authlib.jose.errors import JoseError
from authlib.oauth2 import OAuth2Error
from canaille import csrf
from canaille.app import models
from canaille.app.flask import current_user
from canaille.app.flask import logout_user
from canaille.app.flask import set_parameter_in_url_query
from canaille.app.i18n import gettext as _
from canaille.app.themes import render_template
from flask import abort
from flask import Blueprint
from flask import current_app
from flask import flash
from flask import jsonify
from flask import redirect
from flask import request
from flask import session
from flask import url_for
from werkzeug.datastructures import CombinedMultiDict

from ..oauth import authorization
from ..oauth import ClientConfigurationEndpoint
from ..oauth import ClientRegistrationEndpoint
from ..oauth import generate_user_info
from ..oauth import get_issuer
from ..oauth import get_jwks
from ..oauth import IntrospectionEndpoint
from ..oauth import require_oauth
from ..oauth import RevocationEndpoint
from ..utils import SCOPE_DETAILS
from .forms import AuthorizeForm
from .forms import LogoutForm
from .well_known import openid_configuration


bp = Blueprint("endpoints", __name__, url_prefix="/oauth")


@bp.route("/authorize", methods=["GET", "POST"])
def authorize():
    current_app.logger.debug(
        "authorization endpoint request:\nGET: %s\nPOST: %s",
        request.args.to_dict(flat=False),
        request.form.to_dict(flat=False),
    )

    if "client_id" not in request.args:
        abort(400, "client_id parameter is missing.")

    client = models.Client.get(client_id=request.args["client_id"])
    if not client:
        abort(400, "Invalid client.")

    # https://openid.net/specs/openid-connect-prompt-create-1_0.html#name-authorization-request
    # If the OpenID Provider receives a prompt value that it does
    # not support (not declared in the prompt_values_supported
    # metadata field) the OP SHOULD respond with an HTTP 400 (Bad
    # Request) status code and an error value of invalid_request.
    # It is RECOMMENDED that the OP return an error_description
    # value identifying the invalid parameter value.
    if (
        request.args.get("prompt")
        and request.args["prompt"]
        not in openid_configuration()["prompt_values_supported"]
    ):
        return {
            "error": "invalid_request",
            "error_description": f"prompt '{request.args['prompt'] }' value is not supported",
        }, 400

    user = current_user()
    requested_scopes = request.args.get("scope", "").split(" ")
    allowed_scopes = client.get_allowed_scope(requested_scopes).split(" ")

    # LOGIN

    if not user:
        if request.args.get("prompt") == "none":
            return jsonify({"error": "login_required"})

        session["redirect-after-login"] = request.url

        if request.args.get("prompt") == "create":
            return redirect(url_for("core.account.join"))

        return redirect(url_for("core.auth.login"))

    if not user.can_use_oidc:
        abort(
            403, "The user does not have the permission to achieve OIDC authentication."
        )

    # CONSENT

    consents = models.Consent.query(
        client=client,
        subject=user,
    )
    consent = consents[0] if consents else None

    if request.method == "GET":
        if (
            (client.preconsent and (not consent or not consent.revoked))
            or (
                consent and all(scope in set(consent.scope) for scope in allowed_scopes)
            )
            and not consent.revoked
        ):
            return authorization.create_authorization_response(grant_user=user)

        elif request.args.get("prompt") == "none":
            response = {"error": "consent_required"}
            current_app.logger.debug("authorization endpoint response: %s", response)
            return jsonify(response)

        try:
            grant = authorization.get_consent_grant(end_user=user)
        except OAuth2Error as error:
            response = dict(error.get_body())
            current_app.logger.debug("authorization endpoint response: %s", response)
            return jsonify(response)

        form = AuthorizeForm(request.form or None)
        return render_template(
            "authorize.html",
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
        consent.save()

    response = authorization.create_authorization_response(grant_user=grant_user)
    current_app.logger.debug("authorization endpoint response: %s", response.location)
    return response


@bp.route("/token", methods=["POST"])
@csrf.exempt
def issue_token():
    current_app.logger.debug(
        "token endpoint request: POST: %s", request.form.to_dict(flat=False)
    )
    response = authorization.create_token_response()
    current_app.logger.debug("token endpoint response: %s", response.json)
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
        request.form.to_dict(flat=False),
    )
    response = authorization.create_endpoint_response(
        ClientRegistrationEndpoint.ENDPOINT_NAME
    )
    current_app.logger.debug("client registration endpoint response: %s", response.json)
    return response


@bp.route("/register/<client_id>", methods=["GET", "PUT", "DELETE"])
@csrf.exempt
def client_registration_management(client_id):
    current_app.logger.debug(
        "client registration management endpoint request: POST: %s",
        request.form.to_dict(flat=False),
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
@require_oauth("profile")
def userinfo():
    current_app.logger.debug("userinfo endpoint request: %s", request.args)
    response = generate_user_info(current_token.subject, current_token.scope)
    current_app.logger.debug("userinfo endpoint response: %s", response)
    return jsonify(response)


@bp.route("/end_session", methods=["GET", "POST"])
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
        client = models.Client.get(client_id=data["client_id"])
        if client:
            valid_uris = client.post_logout_redirect_uris

    if (
        not data.get("id_token_hint")
        or (data.get("logout_hint") and data["logout_hint"] != user.user_name)
    ) and not session.get("end_session_confirmation"):
        session["end_session_data"] = data
        return render_template("logout.html", form=form, client=client, menu=False)

    if data.get("id_token_hint"):
        try:
            id_token = jwt.decode(
                data["id_token_hint"], current_app.config["OIDC"]["JWT"]["PUBLIC_KEY"]
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
                client = models.Client.get(client_id=client_id)
                if client:
                    valid_uris.extend(client.post_logout_redirect_uris or [])

        if user.user_name != id_token["sub"] and not session.get(
            "end_session_confirmation"
        ):
            session["end_session_data"] = data
            return render_template("logout.html", form=form, client=client, menu=False)

    logout_user()

    if "end_session_confirmation" in session:
        del session["end_session_confirmation"]

    if (
        "post_logout_redirect_uri" in data
        and data["post_logout_redirect_uri"] in valid_uris
    ):
        url = data["post_logout_redirect_uri"]
        if "state" in data:
            url = set_parameter_in_url_query(url, state=data["state"])
        return redirect(url)

    flash(_("You have been disconnected"), "success")
    return redirect(url_for("core.account.index"))


@bp.route("/end_session_confirm", methods=["POST"])
def end_session_submit():
    form = LogoutForm(request.form)
    form.validate()

    data = session["end_session_data"]
    del session["end_session_data"]

    if request.form["answer"] == "logout":
        session["end_session_confirmation"] = True
        url = set_parameter_in_url_query(url_for("oidc.endpoints.end_session"), **data)
        return redirect(url)

    flash(_("You have not been disconnected"), "info")

    return redirect(url_for("core.account.index"))
