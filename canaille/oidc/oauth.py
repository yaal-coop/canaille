import datetime

from authlib.integrations.flask_oauth2 import current_token
from authlib.jose import jwk
from authlib.oauth2 import OAuth2Error
from flask import abort
from flask import Blueprint
from flask import current_app
from flask import flash
from flask import jsonify
from flask import redirect
from flask import request
from flask import session
from flask_babel import gettext
from flask_babel import lazy_gettext as _
from flask_themer import render_template

from ..flaskutils import current_user
from ..forms import FullLoginForm
from ..models import User
from .models import Client
from .models import Consent
from .oauth2utils import authorization
from .oauth2utils import DEFAULT_JWT_ALG
from .oauth2utils import DEFAULT_JWT_KTY
from .oauth2utils import generate_user_info
from .oauth2utils import IntrospectionEndpoint
from .oauth2utils import require_oauth
from .oauth2utils import RevocationEndpoint


bp = Blueprint("oauth", __name__, url_prefix="/oauth")

CLAIMS = {
    "profile": (
        "id card outline",
        _("Personnal information about yourself, such as your name or your gender."),
    ),
    "email": ("at", _("Your email address.")),
    "address": ("envelope open outline", _("Your postal address.")),
    "phone": ("phone", _("Your phone number.")),
    "groups": ("users", _("Groups you are belonging to")),
}


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
    scopes = request.args.get("scope", "").split(" ")

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
            flash(gettext("Login failed, please check your information"), "error")
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
            grant = authorization.validate_consent_request(end_user=user)
        except OAuth2Error as error:
            response = dict(error.get_body())
            current_app.logger.debug("authorization endpoint response: %s", response)
            return jsonify(response)

        return render_template(
            "oidc/user/authorize.html",
            user=user,
            grant=grant,
            client=client,
            claims=CLAIMS,
            menu=False,
            ignored_claims=["openid"],
        )

    if request.method == "POST":
        if request.form["answer"] == "logout":
            del session["user_dn"]
            flash(gettext("You have been successfully logged out."), "success")
            return redirect(request.url)

        if request.form["answer"] == "deny":
            grant_user = None

        if request.form["answer"] == "accept":
            grant_user = user.dn

            if consent:
                consent.scope = list(set(scopes + consents[0].scope))
            else:

                consent = Consent(
                    client=client.dn,
                    subject=user.dn,
                    scope=scopes,
                    issue_date=datetime.datetime.now(),
                )
            consent.save()

        response = authorization.create_authorization_response(grant_user=grant_user)
        current_app.logger.debug(
            "authorization endpoint response: %s", response.location
        )
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


@bp.route("/jwks.json")
def jwks():
    with open(current_app.config["JWT"]["PUBLIC_KEY"]) as fd:
        pubkey = fd.read()

    obj = jwk.dumps(pubkey, current_app.config["JWT"].get("KTY", DEFAULT_JWT_KTY))
    return jsonify(
        {
            "keys": [
                {
                    "kid": None,
                    "use": "sig",
                    "alg": current_app.config["JWT"].get("ALG", DEFAULT_JWT_ALG),
                    **obj,
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
