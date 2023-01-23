import datetime
import uuid

from authlib.integrations.flask_oauth2 import current_token
from authlib.jose import JsonWebKey
from authlib.jose import jwt
from authlib.oauth2 import OAuth2Error
from flask import abort
from flask import Blueprint
from flask import current_app
from flask import flash
from flask import jsonify
from flask import redirect
from flask import request
from flask import session
from flask import url_for
from flask_babel import gettext as _
from flask_themer import render_template
from werkzeug.datastructures import CombinedMultiDict

from ..flaskutils import current_user
from ..flaskutils import set_parameter_in_url_query
from ..forms import FullLoginForm
from ..models import User
from .forms import LogoutForm
from .models import Client
from .models import Consent
from .oauth import authorization
from .oauth import ClientConfigurationEndpoint
from .oauth import ClientRegistrationEndpoint
from .oauth import DEFAULT_JWT_ALG
from .oauth import DEFAULT_JWT_KTY
from .oauth import generate_user_info
from .oauth import get_issuer
from .oauth import IntrospectionEndpoint
from .oauth import require_oauth
from .oauth import RevocationEndpoint
from .utils import SCOPE_DETAILS


bp = Blueprint("endpoints", __name__, url_prefix="/oauth")


def get_public_key():
    with open(current_app.config["JWT"]["PUBLIC_KEY"]) as fd:
        return fd.read()


@bp.route("/authorize", methods=["GET", "POST"])
def authorize():
    current_app.logger.debug(
        "authorization endpoint request:\nGET: %s\nPOST: %s",
        request.args.to_dict(flat=False),
        request.form.to_dict(flat=False),
    )

    if "client_id" not in request.args:
        abort(400)

    client = Client.get(request.args["client_id"])
    if not client:
        abort(400)

    user = current_user()
    scopes = client.get_allowed_scope(request.args.get("scope", "").split(" ")).split(
        " "
    )

    # LOGIN

    if not user:
        if request.args.get("prompt") == "none":
            return jsonify({"error": "login_required"})

        form = FullLoginForm(request.form or None)
        if request.method == "GET":
            return render_template("login.html", form=form, menu=False)

        if not form.validate() or not User.authenticate(
            form.login.data, form.password.data, True
        ):
            flash(_("Login failed, please check your information"), "error")
            return render_template("login.html", form=form, menu=False)

        return redirect(request.url)

    if not user.can_use_oidc:
        abort(400)

    # CONSENT

    consents = Consent.filter(
        client=client.dn,
        subject=user.dn,
    )
    consents = [c for c in consents if not c.revokation_date]
    consent = consents[0] if consents else None

    if request.method == "GET":
        if client.preconsent or (
            consent and all(scope in set(consent.scope) for scope in scopes)
        ):
            return authorization.create_authorization_response(grant_user=user.dn)

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

        return render_template(
            "oidc/user/authorize.html",
            user=user,
            grant=grant,
            client=client,
            menu=False,
            scope_details=SCOPE_DETAILS,
            ignored_scopes=["openid"],
        )

    # request.method == "POST"
    if request.form["answer"] == "logout":
        del session["user_id"]
        flash(_("You have been successfully logged out."), "success")
        return redirect(request.url)

    if request.form["answer"] == "deny":
        grant_user = None

    if request.form["answer"] == "accept":
        grant_user = user.dn

        if consent:
            consent.scope = client.get_allowed_scope(
                list(set(scopes + consents[0].scope))
            ).split(" ")
        else:
            consent = Consent(
                cn=str(uuid.uuid4()),
                client=client.dn,
                subject=user.dn,
                scope=scopes,
                issue_date=datetime.datetime.now(),
            )
        consent.save()

    response = authorization.create_authorization_response(grant_user=grant_user)
    current_app.logger.debug("authorization endpoint response: %s", response.location)
    return response


@bp.route("/token", methods=["POST"])
def issue_token():
    current_app.logger.debug(
        "token endpoint request: POST: %s", request.form.to_dict(flat=False)
    )
    response = authorization.create_token_response()
    current_app.logger.debug("token endpoint response: %s", response.json)
    return response


@bp.route("/introspect", methods=["POST"])
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
def revoke_token():
    current_app.logger.debug(
        "revokation endpoint request: POST: %s", request.form.to_dict(flat=False)
    )
    response = authorization.create_endpoint_response(RevocationEndpoint.ENDPOINT_NAME)
    current_app.logger.debug("revokation endpoint response: %s", response.json)
    return response


@bp.route("/register", methods=["POST"])
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
    kty = current_app.config["JWT"].get("KTY", DEFAULT_JWT_KTY)
    alg = current_app.config["JWT"].get("ALG", DEFAULT_JWT_ALG)
    jwk = JsonWebKey.import_key(get_public_key(), {"kty": kty})
    return jsonify(
        {
            "keys": [
                {
                    "kid": None,
                    "use": "sig",
                    "alg": alg,
                    **jwk,
                }
            ]
        }
    )


@bp.route("/userinfo")
@require_oauth("profile")
def userinfo():
    current_app.logger.debug("userinfo endpoint request: %s", request.args)
    response = generate_user_info(current_token.subject, current_token.scope[0])
    current_app.logger.debug("userinfo endpoint response: %s", response)
    return jsonify(response)


@bp.route("/end_session", methods=["GET", "POST"])
def end_session():
    data = CombinedMultiDict((request.args, request.form))
    user = current_user()

    if not user:
        return redirect(url_for("account.index"))

    form = LogoutForm(request.form)
    form.action = url_for("oidc.endpoints.end_session_submit")

    client = None
    valid_uris = []

    if "client_id" in data:
        client = Client.get(data["client_id"])
        if client:
            valid_uris = client.post_logout_redirect_uris

    if (
        not data.get("id_token_hint")
        or (data.get("logout_hint") and data["logout_hint"] != user.uid[0])
    ) and not session.get("end_session_confirmation"):
        session["end_session_data"] = data
        return render_template(
            "oidc/user/logout.html", form=form, client=client, menu=False
        )

    if data.get("id_token_hint"):
        id_token = jwt.decode(data["id_token_hint"], get_public_key())
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
                        "message": "id_token_hint and client_id don't match",
                    }
                )

        else:
            client_ids = (
                id_token["aud"]
                if isinstance(id_token["aud"], list)
                else [id_token["aud"]]
            )
            for client_id in client_ids:
                client = Client.get(client_id)
                if client:
                    valid_uris.extend(client.post_logout_redirect_uris or [])

        if user.uid[0] != id_token["sub"] and not session.get(
            "end_session_confirmation"
        ):
            session["end_session_data"] = data
            return render_template(
                "oidc/user/logout.html", form=form, client=client, menu=False
            )

    user.logout()

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
    return redirect(url_for("account.index"))


@bp.route("/end_session_confirm", methods=["POST"])
def end_session_submit():
    form = LogoutForm(request.form)
    if not form.validate():
        flash(_("An error happened during the logout"), "error")
        client = Client.get(session.get("end_session_data", {}).get("client_id"))
        return render_template("oidc/user/logout.html", form=form, client=client)

    data = session["end_session_data"]
    del session["end_session_data"]

    if request.form["answer"] == "logout":
        session["end_session_confirmation"] = True
        url = set_parameter_in_url_query(url_for("oidc.endpoints.end_session"), **data)
        return redirect(url)

    flash(_("You have not been disconnected"), "info")

    return redirect(url_for("account.index"))
