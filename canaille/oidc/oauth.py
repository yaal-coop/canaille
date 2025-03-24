import datetime
import json

import httpx
from authlib.integrations.flask_oauth2 import AuthorizationServer
from authlib.integrations.flask_oauth2 import ResourceProtector
from authlib.jose import JsonWebKey
from authlib.oauth2.rfc6749 import InvalidClientError
from authlib.oauth2.rfc6749.grants import (
    AuthorizationCodeGrant as _AuthorizationCodeGrant,
)
from authlib.oauth2.rfc6749.grants import ClientCredentialsGrant
from authlib.oauth2.rfc6749.grants import ImplicitGrant
from authlib.oauth2.rfc6749.grants import RefreshTokenGrant as _RefreshTokenGrant
from authlib.oauth2.rfc6749.grants import (
    ResourceOwnerPasswordCredentialsGrant as _ResourceOwnerPasswordCredentialsGrant,
)
from authlib.oauth2.rfc6750 import BearerTokenValidator as _BearerTokenValidator
from authlib.oauth2.rfc7009 import RevocationEndpoint as _RevocationEndpoint
from authlib.oauth2.rfc7523 import JWTBearerClientAssertion
from authlib.oauth2.rfc7523 import JWTBearerGrant as _JWTBearerGrant
from authlib.oauth2.rfc7591 import ClientMetadataClaims as OAuth2ClientMetadataClaims
from authlib.oauth2.rfc7591 import (
    ClientRegistrationEndpoint as _ClientRegistrationEndpoint,
)
from authlib.oauth2.rfc7592 import (
    ClientConfigurationEndpoint as _ClientConfigurationEndpoint,
)
from authlib.oauth2.rfc7636 import CodeChallenge as _CodeChallenge
from authlib.oauth2.rfc7662 import IntrospectionEndpoint as _IntrospectionEndpoint
from authlib.oauth2.rfc8414 import AuthorizationServerMetadata
from authlib.oauth2.rfc9207.parameter import IssuerParameter as _IssuerParameter
from authlib.oidc.core import UserInfo
from authlib.oidc.core.grants import OpenIDCode as _OpenIDCode
from authlib.oidc.core.grants import OpenIDHybridGrant as _OpenIDHybridGrant
from authlib.oidc.core.grants import OpenIDImplicitGrant as _OpenIDImplicitGrant
from authlib.oidc.core.grants.util import generate_id_token
from authlib.oidc.discovery import OpenIDProviderMetadata
from authlib.oidc.registration import ClientMetadataClaims as OIDCClientMetadataClaims
from flask import current_app
from flask import g
from flask import request
from flask import url_for
from joserfc.jwk import JWKRegistry
from joserfc.jwk import KeySet
from werkzeug.security import gen_salt

from canaille.app import DOCUMENTATION_URL
from canaille.app import models
from canaille.app.flask import cache
from canaille.backends import Backend
from canaille.core.auth import get_user_from_login

AUTHORIZATION_CODE_LIFETIME = 84400
JWT_JTI_CACHE_LIFETIME = 3600


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
        "token_endpoint_auth_signing_alg_values_supported": ["RS256", "ES256"],
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
    prompt_values_supported = ["none"] + (
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
        "id_token_signing_alg_values_supported": ["RS256", "ES256", "HS256"],
        "id_token_encryption_alg_values_supported": None,
        "id_token_encryption_enc_values_supported": None,
        "userinfo_signing_alg_values_supported": ["RS256"],
        "userinfo_encryption_alg_values_supported": None,
        "userinfo_encryption_enc_values_supported": None,
        "prompt_values_supported": prompt_values_supported,
        "request_parameter_supported": False,
        "request_uri_parameter_supported": False,
        "require_request_uri_registration": False,
        "request_object_signing_alg_values_supported": ["none", "RS256"],
        "request_object_encryption_alg_values_supported": None,
        "request_object_encryption_enc_values_supported": None,
        "response_modes_supported": ["query", "fragment"],
        "acr_values_supported": None,
        "display_values_supported": None,
    }
    obj = OpenIDProviderMetadata(payload)
    obj.validate()
    return obj


def exists_nonce(nonce, req):
    client = Backend.instance.get(models.Client, id=req.client_id)
    exists = Backend.instance.query(
        models.AuthorizationCode, client=client, nonce=nonce
    )
    return bool(exists)


def get_issuer():
    if current_app.config["CANAILLE_OIDC"]["JWT"]["ISS"]:
        return current_app.config["CANAILLE_OIDC"]["JWT"]["ISS"]

    if current_app.config.get("SERVER_NAME"):
        return current_app.config.get("SERVER_NAME")

    return request.url_root


def get_jwt_config(grant=None):
    return {
        "key": current_app.config["CANAILLE_OIDC"]["JWT"]["PRIVATE_KEY"],
        "alg": current_app.config["CANAILLE_OIDC"]["JWT"]["ALG"],
        "iss": get_issuer(),
        "exp": current_app.config["CANAILLE_OIDC"]["JWT"]["EXP"],
    }


def get_jwks():
    kty = current_app.config["CANAILLE_OIDC"]["JWT"]["KTY"]
    alg = current_app.config["CANAILLE_OIDC"]["JWT"]["ALG"]
    jwk = JWKRegistry.import_key(
        current_app.config["CANAILLE_OIDC"]["JWT"]["PUBLIC_KEY"],
        kty,
        {"alg": alg, "use": "sig"},
    )
    jwk.ensure_kid()
    key_set = KeySet([jwk])
    return key_set.as_dict()


def get_client_jwks(client, kid=None):
    """Get the client JWK set, either stored locally or by downloading them from the URI the client indicated."""

    @cache.cached(timeout=50, key_prefix=f"jwks_{client.client_id}")
    def get_jwks():
        return httpx.get(client.jwks_uri).json()

    if client.jwks_uri:
        raw_jwks = get_jwks()
        key_set = JsonWebKey.import_key_set(raw_jwks)
        jwk = key_set.find_by_kid(kid)
        return jwk

    if client.jwks:
        raw_jwks = json.loads(client.jwks)
        key_set = JsonWebKey.import_key_set(raw_jwks)
        jwk = key_set.find_by_kid(kid)
        return jwk

    return None


def claims_from_scope(scope):
    claims = {"sub"}
    if "profile" in scope:
        claims |= {
            "name",
            "family_name",
            "given_name",
            "nickname",
            "preferred_username",
            "profile",
            "picture",
            "website",
            "gender",
            "birthdate",
            "zoneinfo",
            "locale",
            "updated_at",
        }
    if "email" in scope:
        claims |= {"email", "email_verified"}
    if "address" in scope:
        claims |= {"address"}
    if "phone" in scope:
        claims |= {"phone_number", "phone_number_verified"}
    if "groups" in scope:
        claims |= {"groups"}
    return claims


def generate_user_info(user, scope):
    claims = claims_from_scope(scope)
    data = generate_user_claims(user, claims)
    return UserInfo(**data)


def generate_user_claims(user, claims, jwt_mapping_config=None):
    jwt_mapping_config = {
        **(current_app.config["CANAILLE_OIDC"]["JWT"]["MAPPING"]),
        **(jwt_mapping_config or {}),
    }

    data = {}
    for claim in claims:
        raw_claim = jwt_mapping_config.get(claim.upper())
        if raw_claim:
            formatted_claim = current_app.jinja_env.from_string(raw_claim).render(
                user=user
            )
            if formatted_claim:
                # According to https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse
                # it's better to not insert a null or empty string value
                data[claim] = formatted_claim
        if claim == "groups":
            data[claim] = [group.display_name for group in user.groups]
    return data


def save_authorization_code(code, request):
    nonce = request.data.get("nonce")
    now = datetime.datetime.now(datetime.timezone.utc)
    scope = request.client.get_allowed_scope(request.scope)
    code = models.AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code=code,
        subject=request.user,
        client=request.client,
        redirect_uri=request.redirect_uri or request.client.redirect_uris[0],
        scope=scope.split(" "),
        nonce=nonce,
        issue_date=now,
        lifetime=AUTHORIZATION_CODE_LIFETIME,
        challenge=request.data.get("code_challenge"),
        challenge_method=request.data.get("code_challenge_method"),
    )
    Backend.instance.save(code)
    return code.code


class JWTClientAuth(JWTBearerClientAssertion):
    def validate_jti(self, claims, jti):
        """Indicate whether the jti was used before."""
        key = "jti:{}-{}".format(claims["sub"], jti)
        if cache.get(key):
            return False
        cache.set(key, 1, timeout=JWT_JTI_CACHE_LIFETIME)
        return True

    def resolve_client_public_key(self, client, headers):
        jwk = get_client_jwks(client)
        if not jwk:
            raise InvalidClientError(description="No matching JWK")

        return jwk


class AuthorizationCodeGrant(_AuthorizationCodeGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = [
        "client_secret_basic",
        "client_secret_post",
        JWTClientAuth.CLIENT_AUTH_METHOD,
        "none",
    ]

    def save_authorization_code(self, code, request):
        return save_authorization_code(code, request)

    def query_authorization_code(self, code, client):
        item = Backend.instance.query(
            models.AuthorizationCode, code=code, client=client
        )
        if item and not item[0].is_expired():
            return item[0]

    def delete_authorization_code(self, authorization_code):
        Backend.instance.delete(authorization_code)

    def authenticate_user(self, authorization_code):
        if authorization_code.subject and not authorization_code.subject.locked:
            return authorization_code.subject


class OpenIDCode(_OpenIDCode):
    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_jwt_config(self, grant):
        return get_jwt_config(grant)

    def generate_user_info(self, user, scope):
        return generate_user_info(user, scope)

    def get_audiences(self, request):
        client = request.client
        return [aud.client_id for aud in client.audience]


class PasswordGrant(_ResourceOwnerPasswordCredentialsGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post", "none"]

    def authenticate_user(self, username, password):
        user = get_user_from_login(username)
        if not user:
            return None

        success, _ = Backend.instance.check_user_password(user, password)
        if not success:
            return None

        return user


class RefreshTokenGrant(_RefreshTokenGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post", "none"]

    def authenticate_refresh_token(self, refresh_token):
        token = Backend.instance.query(models.Token, refresh_token=refresh_token)
        if token and token[0].is_refresh_token_active():
            return token[0]

    def authenticate_user(self, credential):
        if credential.subject and not credential.subject.locked:
            return credential.subject

    def revoke_old_credential(self, credential):
        credential.revokation_date = datetime.datetime.now(datetime.timezone.utc)
        Backend.instance.save(credential)


class JWTBearerGrant(_JWTBearerGrant):
    def resolve_issuer_client(self, issuer):
        return Backend.instance.get(models.Client, client_id=issuer)

    def resolve_client_key(self, client, headers, payload):
        jwk = get_client_jwks(client, headers.get("kid"))
        if not jwk:
            raise InvalidClientError(description="No matching JWK")
        return jwk

    def authenticate_user(self, subject: str):
        return get_user_from_login(subject)

    def has_granted_permission(self, client, user):
        grant = Backend.instance.get(models.Consent, client=client, subject=user)
        has_permission = (grant and not grant.revoked) or (not grant and client.trusted)
        return has_permission


class OpenIDImplicitGrant(_OpenIDImplicitGrant):
    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_jwt_config(self, grant=None):
        return get_jwt_config(grant)

    def generate_user_info(self, user, scope):
        return generate_user_info(user, scope)

    def get_audiences(self, request):
        client = request.client
        return [aud.client_id for aud in client.audience]


class OpenIDHybridGrant(_OpenIDHybridGrant):
    def save_authorization_code(self, code, request):
        return save_authorization_code(code, request)

    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_jwt_config(self, grant=None):
        return get_jwt_config(grant)

    def generate_user_info(self, user, scope):
        return generate_user_info(user, scope)

    def get_audiences(self, request):
        client = request.client
        return [aud.client_id for aud in client.audience]


def query_client(client_id):
    return Backend.instance.get(models.Client, client_id=client_id)


def save_token(token, request):
    now = datetime.datetime.now(datetime.timezone.utc)
    t = models.Token(
        token_id=gen_salt(48),
        type=token["token_type"],
        access_token=token["access_token"],
        issue_date=now,
        lifetime=token["expires_in"],
        scope=token["scope"].split(" "),
        client=request.client,
        refresh_token=token.get("refresh_token"),
        subject=request.user,
        audience=request.client.audience,
    )
    Backend.instance.save(t)


class BearerTokenValidator(_BearerTokenValidator):
    def authenticate_token(self, token_string):
        return Backend.instance.get(models.Token, access_token=token_string)


def query_token(token, token_type_hint):
    if token_type_hint == "access_token":
        return Backend.instance.get(models.Token, access_token=token)
    elif token_type_hint == "refresh_token":
        return Backend.instance.get(models.Token, refresh_token=token)

    item = Backend.instance.get(models.Token, access_token=token)
    if item:
        return item

    item = Backend.instance.get(models.Token, refresh_token=token)
    if item:
        return item

    return None


class RevocationEndpoint(_RevocationEndpoint):
    def query_token(self, token, token_type_hint):
        return query_token(token, token_type_hint)

    def revoke_token(self, token, request):
        token.revokation_date = datetime.datetime.now(datetime.timezone.utc)
        Backend.instance.save(token)


class IntrospectionEndpoint(_IntrospectionEndpoint):
    def query_token(self, token, token_type_hint):
        return query_token(token, token_type_hint)

    def check_permission(self, token, client, request):
        return client in token.audience

    def introspect_token(self, token):
        audience = [aud.client_id for aud in token.audience]
        response = {
            "active": True,
            "client_id": token.client.client_id,
            "token_type": token.type,
            "scope": token.get_scope(),
            "aud": audience,
            "iss": get_issuer(),
            "exp": token.get_expires_at(),
            "iat": token.get_issued_at(),
        }
        if token.subject:
            response["username"] = token.subject.formatted_name
            response["sub"] = token.subject.user_name
        return response


class ClientManagementMixin:
    def authenticate_token(self, request):
        if current_app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_OPEN"]:
            return True

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return None

        bearer_token = auth_header.split()[1]
        if bearer_token not in (
            current_app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_TOKENS"]
            or []
        ):
            return None

        return True

    def get_server_metadata(self):
        result = openid_configuration()
        return result

    def resolve_public_key(self, request):
        # At the moment the only keypair accepted in software statement
        # is the one used to issues JWTs. This might change somedays.
        return current_app.config["CANAILLE_OIDC"]["JWT"]["PUBLIC_KEY"]

    def client_convert_data(self, **kwargs):
        if "client_id_issued_at" in kwargs:
            kwargs["client_id_issued_at"] = datetime.datetime.fromtimestamp(
                kwargs["client_id_issued_at"], datetime.timezone.utc
            )

        if "client_secret_expires_at" in kwargs:
            kwargs["client_secret_expires_at"] = datetime.datetime.fromtimestamp(
                kwargs["client_secret_expires_at"], datetime.timezone.utc
            )

        if "jwks" in kwargs:
            kwargs["jwks"] = json.dumps(kwargs["jwks"])

        kwargs["scope"] = kwargs["scope"].split(" ")

        return kwargs


class ClientRegistrationEndpoint(ClientManagementMixin, _ClientRegistrationEndpoint):
    software_statement_alg_values_supported = ["RS256"]

    def generate_client_registration_info(self, client, request):
        return {"scope": " ".join(client.scope)}

    def save_client(self, client_info, client_metadata, request):
        if "scope" not in client_metadata:
            client_metadata["scope"] = "openid"

        client = models.Client(
            # this won't be needed when OIDC RP Initiated Logout is
            # directly implemented in authlib:
            # https://gitlab.com/yaal/canaille/-/issues/157
            post_logout_redirect_uris=request.data.get("post_logout_redirect_uris"),
            **self.client_convert_data(**client_info, **client_metadata),
        )
        Backend.instance.save(client)
        client.audience = [client]
        Backend.instance.save(client)
        return client


class ClientConfigurationEndpoint(ClientManagementMixin, _ClientConfigurationEndpoint):
    def authenticate_client(self, request):
        client_id = request.uri.split("/")[-1]
        return Backend.instance.get(models.Client, client_id=client_id)

    def revoke_access_token(self, request, token):
        pass

    def check_permission(self, client, request):
        return True

    def delete_client(self, client, request):
        Backend.instance.delete(client)

    def update_client(self, client, client_metadata, request):
        Backend.instance.update(client, **self.client_convert_data(**client_metadata))
        Backend.instance.save(client)
        return client

    def generate_client_registration_info(self, client, request):
        access_token = request.headers["Authorization"].split(" ")[1]
        return {
            "registration_client_uri": request.uri,
            "registration_access_token": access_token,
        }


class CodeChallenge(_CodeChallenge):
    def get_authorization_code_challenge(self, authorization_code):
        return authorization_code.challenge

    def get_authorization_code_challenge_method(self, authorization_code):
        return authorization_code.challenge_method


class IssuerParameter(_IssuerParameter):
    def get_issuer(self) -> str:
        return get_issuer()


authorization = AuthorizationServer()
require_oauth = ResourceProtector()


def generate_access_token(client, grant_type, user, scope):
    if grant_type == "client_credentials":
        # Canaille could generate a JWT with iss/sub/aud/exp/iat/jti/scope/client_id
        # instead of a random string
        return gen_salt(48)

    audience = [client.client_id for client in client.audience]
    bearer_token_generator = authorization._token_generators["default"]
    kwargs = {
        "token": {},
        "user_info": generate_user_info(user, scope),
        "aud": audience,
        **get_jwt_config(grant_type),
    }
    kwargs["exp"] = bearer_token_generator._get_expires_in(client, grant_type)
    return generate_id_token(**kwargs)


def setup_oauth(app):
    app.config["OAUTH2_REFRESH_TOKEN_GENERATOR"] = True
    app.config["OAUTH2_ACCESS_TOKEN_GENERATOR"] = (
        "canaille.oidc.oauth.generate_access_token"
    )

    # hacky, but needed for tests as somehow the same 'authorization' object is used
    # between tests
    authorization.__init__()
    authorization.init_app(app, query_client=query_client, save_token=save_token)

    authorization.register_grant(PasswordGrant)
    authorization.register_grant(ImplicitGrant)
    authorization.register_grant(RefreshTokenGrant)
    authorization.register_grant(JWTBearerGrant)
    authorization.register_grant(ClientCredentialsGrant)

    with app.app_context():
        if not app.config["SERVER_NAME"]:
            app.logger.warning(
                "The 'SERVER_NAME' configuration parameter is unset. JWT client authentication is disabled."
            )

        else:
            authorization.register_client_auth_method(
                JWTClientAuth.CLIENT_AUTH_METHOD,
                JWTClientAuth(url_for("oidc.endpoints.issue_token", _external=True)),
            )

    authorization.register_grant(
        AuthorizationCodeGrant,
        [
            IssuerParameter(),
            OpenIDCode(require_nonce=app.config["CANAILLE_OIDC"]["REQUIRE_NONCE"]),
            CodeChallenge(required=True),
        ],
    )
    authorization.register_grant(OpenIDImplicitGrant)
    authorization.register_grant(OpenIDHybridGrant)

    require_oauth.register_token_validator(BearerTokenValidator())

    authorization.register_endpoint(IntrospectionEndpoint)
    authorization.register_endpoint(RevocationEndpoint)
    authorization.register_endpoint(
        ClientRegistrationEndpoint(
            claims_classes=[OAuth2ClientMetadataClaims, OIDCClientMetadataClaims]
        )
    )
    authorization.register_endpoint(
        ClientConfigurationEndpoint(
            claims_classes=[OAuth2ClientMetadataClaims, OIDCClientMetadataClaims]
        )
    )
