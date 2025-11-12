from authlib.oauth2 import rfc8414
from authlib.oauth2 import rfc9101
from authlib.oidc import discovery as oidc_discovery
from flask import current_app
from flask import g
from flask import url_for

from canaille.app import DOCUMENTATION_URL

from .provider import CodeChallenge
from .provider import get_issuer


class AuthorizationServerMetadata(
    rfc8414.AuthorizationServerMetadata, rfc9101.AuthorizationServerMetadata
):
    pass


def oauth_authorization_server():
    payload = {
        "issuer": get_issuer(),
        "authorization_endpoint": url_for("oidc.endpoints.authorize", _external=True),
        "token_endpoint": url_for("oidc.endpoints.issue_token", _external=True),
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "private_key_jwt",
            "client_secret_post",
            "none",
        ],
        "token_endpoint_auth_signing_alg_values_supported": [
            "RS256",
            "ES256",
            "HS256",
            "EdDSA",
        ],
        "userinfo_endpoint": url_for("oidc.endpoints.userinfo", _external=True),
        "revocation_endpoint": url_for("oidc.endpoints.revoke_token", _external=True),
        "revocation_endpoint_auth_methods_supported": ["client_secret_basic"],
        "revocation_endpoint_auth_signing_alg_values_supported": None,
        "introspection_endpoint": url_for(
            "oidc.endpoints.introspect_token", _external=True
        ),
        "introspection_endpoint_auth_methods_supported": ["client_secret_basic"],
        "introspection_endpoint_auth_signing_alg_values_supported": None,
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
            "code id_token token",
        ],
        "grant_types_supported": [
            "authorization_code",
            "implicit",
            "password",
            "client_credentials",
            "refresh_token",
        ],
        "ui_locales_supported": g.available_language_codes,
        "code_challenge_methods_supported": CodeChallenge.SUPPORTED_CODE_CHALLENGE_METHOD,
        "service_documentation": DOCUMENTATION_URL,
        "authorization_response_iss_parameter_supported": True,
        "op_policy_uri": None,
        "op_tos_uri": None,
    }
    obj = AuthorizationServerMetadata(payload)
    obj.validate()
    return obj


def openid_configuration():
    prompt_values_supported = ["none", "login", "consent", "select_account"] + (
        ["create"] if current_app.config["CANAILLE"]["ENABLE_REGISTRATION"] else []
    )
    payload = {
        **oauth_authorization_server(),
        "end_session_endpoint": url_for("oidc.endpoints.end_session", _external=True),
        "claim_types_supported": ["normal"],
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
            "nonce",
        ],
        "claims_locales_supported": None,
        "claims_parameter_supported": False,
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": [
            "none",
            "RS256",
            "ES256",
            "HS256",
            "EdDSA",
        ],
        "id_token_encryption_alg_values_supported": None,
        "id_token_encryption_enc_values_supported": None,
        "userinfo_signing_alg_values_supported": [
            "none",
            "RS256",
            "ES256",
            "HS256",
            "EdDSA",
        ],
        "userinfo_encryption_alg_values_supported": None,
        "userinfo_encryption_enc_values_supported": None,
        "prompt_values_supported": prompt_values_supported,
        "request_parameter_supported": True,
        "request_uri_parameter_supported": True,
        "require_request_uri_registration": False,
        "request_object_signing_alg_values_supported": [
            "none",
            "RS256",
            "ES256",
            "HS256",
            "EdDSA",
        ],
        "request_object_encryption_alg_values_supported": None,
        "request_object_encryption_enc_values_supported": None,
        "response_modes_supported": ["query", "fragment"],
        "acr_values_supported": None,
        "display_values_supported": None,
    }
    obj = oidc_discovery.OpenIDProviderMetadata(payload)
    obj.validate()
    return obj
