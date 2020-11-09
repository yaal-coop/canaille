import datetime
from authlib.integrations.flask_oauth2 import current_token
from authlib.jose import jwk
from authlib.oauth2 import OAuth2Error
from flask import Blueprint, request, session, redirect, abort
from flask import render_template, jsonify, flash, current_app
from flask_babel import gettext, lazy_gettext as _
from .models import User, Client, Consent
from .oauth2utils import (
    authorization,
    IntrospectionEndpoint,
    RevocationEndpoint,
    generate_user_info,
    require_oauth,
)
from .forms import LoginForm
from .flaskutils import current_user


bp = Blueprint(__name__, "oauth")

CLAIMS = {
    "profile": (
        "id card outline",
        _("Personnal information about yourself, such as your name or your gender."),
    ),
    "email": ("at", _("Your email address.")),
    "address": ("envelope open outline", _("Your postal address.")),
    "phone": ("phone", _("Your phone number.")),
}


@bp.route("/authorize", methods=["GET", "POST"])
def authorize():
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

        form = LoginForm(request.form or None)
        if request.method == "GET":
            return render_template("login.html", form=form, menu=False)

        if not form.validate() or not User.authenticate(
            form.login.data, form.password.data, True
        ):
            flash(gettext("Login failed, please check your information"), "error")
            return render_template("login.html", form=form, menu=False)

        return redirect(request.url)

    # CONSENT

    consents = Consent.filter(
        oauthClient=client.dn,
        oauthSubject=user.dn,
    )
    consents = [c for c in consents if not c.oauthRevokationDate]
    consent = consents[0] if consents else None

    if request.method == "GET":
        if consent and all(scope in set(consent.oauthScope) for scope in scopes):
            return authorization.create_authorization_response(grant_user=user.dn)

        elif request.args.get("prompt") == "none":
            return jsonify({"error": "consent_required"})

        try:
            grant = authorization.validate_consent_request(end_user=user)
        except OAuth2Error as error:
            return jsonify(dict(error.get_body()))

        return render_template(
            "authorize.html",
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
                consent.oauthScope = list(set(scopes + consents[0].oauthScope))
            else:

                consent = Consent(
                    oauthClient=client.dn,
                    oauthSubject=user.dn,
                    oauthScope=scopes,
                    oauthIssueDate=datetime.datetime.now().strftime("%Y%m%d%H%M%SZ"),
                )
                consent.save()

        return authorization.create_authorization_response(grant_user=grant_user)


@bp.route("/token", methods=["POST"])
def issue_token():
    return authorization.create_token_response()


@bp.route("/introspect", methods=["POST"])
def introspect_token():
    return authorization.create_endpoint_response(IntrospectionEndpoint.ENDPOINT_NAME)


@bp.route("/revoke", methods=["POST"])
def revoke_token():
    return authorization.create_endpoint_response(RevocationEndpoint.ENDPOINT_NAME)


@bp.route("/jwks.json")
def jwks():
    with open(current_app.config["JWT"]["PUBLIC_KEY"]) as fd:
        pubkey = fd.read()

    obj = jwk.dumps(pubkey, current_app.config["JWT"]["KTY"])
    return jsonify(
        {
            "keys": [
                {
                    "kid": None,
                    "use": "sig",
                    "alg": current_app.config["JWT"]["ALG"],
                    **obj,
                }
            ]
        }
    )


@bp.route("/userinfo")
@require_oauth("profile")
def userinfo():
    return jsonify(
        generate_user_info(current_token.oauthSubject, current_token.oauthScope[0])
    )
