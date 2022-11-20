import json

from flask import Blueprint
from flask import current_app
from flask import g
from flask import jsonify
from flask import request
from flask import url_for

from .oauth import get_issuer


bp = Blueprint("home", __name__, url_prefix="/.well-known")


def cached_oauth_authorization_server():
    if "oauth_authorization_server" in g:
        return g.oauth_authorization_server

    g.oauth_authorization_server = {
        "issuer": get_issuer(),
        "authorization_endpoint": url_for("oidc.endpoints.authorize", _external=True),
        "token_endpoint": url_for("oidc.endpoints.issue_token", _external=True),
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "private_key_jwt",
            "client_secret_post",
            "none",
        ],
        "token_endpoint_auth_signing_alg_values_supported": ["RS256", "ES256"],
        "userinfo_endpoint": url_for("oidc.endpoints.userinfo", _external=True),
        "introspection_endpoint": url_for(
            "oidc.endpoints.introspect_token", _external=True
        ),
        "jwks_uri": url_for("oidc.endpoints.jwks", _external=True),
        "registration_endpoint": url_for(
            "oidc.endpoints.client_registration", _external=True
        ),
        "scopes_supported": [
            "openid",
            "profile",
            "email",
            "address",
            "phone",
            "groups",
        ],
        "response_types_supported": [
            "code",
            "token",
            "id_token",
            "code token",
            "code id_token",
            "token id_token",
        ],
        "ui_locales_supported": g.available_language_codes,
        "code_challenge_methods_supported": ["plain", "S256"],
    }

    return g.oauth_authorization_server


def cached_openid_configuration():
    if "openid_configuration" in g:
        return g.openid_configuration

    g.openid_configuration = {
        **cached_oauth_authorization_server(),
        "end_session_endpoint": url_for("oidc.endpoints.end_session", _external=True),
        "claims_supported": [
            "sub",
            "iss",
            "auth_time",
            "acr",
            "name",
            "given_name",
            "family_name",
            "nickname",
            "profile",
            "picture",
            "website",
            "email",
            "email_verified",
            "locale",
            "zoneinfo",
            "groups",
        ],
        "subject_types_supported": ["pairwise", "public"],
        "id_token_signing_alg_values_supported": ["RS256", "ES256", "HS256"],
    }

    return g.openid_configuration


@bp.route("/oauth-authorization-server")
def oauth_authorization_server():
    return jsonify(cached_oauth_authorization_server())


@bp.route("/openid-configuration")
def openid_configuration():
    return jsonify(cached_openid_configuration())


@bp.route("/webfinger")
def webfinger():
    return jsonify(
        {
            "links": [
                {
                    "href": cached_openid_configuration()["issuer"],
                    "rel": "http://openid.net/specs/connect/1.0/issuer",
                }
            ],
            "subject": request.args["resource"],
        }
    )
