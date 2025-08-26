import datetime
import json

import httpx
from authlib.integrations.flask_oauth2 import AuthorizationServer
from authlib.integrations.flask_oauth2 import ResourceProtector
from authlib.oauth2 import rfc6749
from authlib.oauth2 import rfc6750
from authlib.oauth2 import rfc7009
from authlib.oauth2 import rfc7523
from authlib.oauth2 import rfc7591
from authlib.oauth2 import rfc7592
from authlib.oauth2 import rfc7636
from authlib.oauth2 import rfc7662
from authlib.oauth2 import rfc8414
from authlib.oauth2 import rfc9101
from authlib.oauth2 import rfc9207
from authlib.oauth2.rfc6749 import InvalidClientError
from authlib.oidc import core as oidc_core
from authlib.oidc import discovery as oidc_discovery
from authlib.oidc import registration as oidc_registration
from authlib.oidc.core.grants.util import generate_id_token
from flask import current_app
from flask import g
from flask import request
from flask import url_for
from joserfc import jwk
from joserfc import jws
from werkzeug.security import gen_salt

from canaille.app import DOCUMENTATION_URL
from canaille.app import models
from canaille.app.flask import cache
from canaille.backends import Backend
from canaille.core.auth import get_user_from_login

from .jwk import make_default_jwk

AUTHORIZATION_CODE_LIFETIME = 84400
JWT_JTI_CACHE_LIFETIME = 3600

registry = jws.JWSRegistry(algorithms=list(jws.JWSRegistry.algorithms.keys()))


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
    obj = rfc8414.AuthorizationServerMetadata(payload)
    obj.validate()
    return obj


def openid_configuration():
    prompt_values_supported = ["none", "login", "consent"] + (
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


def exists_nonce(nonce, request):
    client = Backend.instance.get(models.Client, id=request.payload.client_id)
    exists = Backend.instance.query(
        models.AuthorizationCode, client=client, nonce=nonce
    )
    return bool(exists)


def get_alg_for_key(key):
    """Find the algorithm for the given key."""
    # TODO: Improve this when a better solution is implemented upstream
    # https://github.com/authlib/joserfc/issues/49
    for alg_name, alg in registry.algorithms.items():  # pragma: no cover
        if alg.key_type == key.key_type:
            return alg_name


def get_issuer():
    if server_name := current_app.config.get("SERVER_NAME"):
        scheme = current_app.config.get("PREFERRED_URL_SCHEME", "http")
        return f"{scheme}://{server_name}"

    return request.url_root


def server_jwks(include_inactive=True):
    keys = current_app.config["CANAILLE_OIDC"]["ACTIVE_JWKS"]
    if include_inactive and current_app.config["CANAILLE_OIDC"]["INACTIVE_JWKS"]:
        keys += current_app.config["CANAILLE_OIDC"]["INACTIVE_JWKS"]

    key_objs = [jwk.import_key(key) for key in keys if key]
    for obj in key_objs:
        obj.ensure_kid()
    return jwk.KeySet(key_objs)


def get_jwt_config(grant=None):
    jwks = server_jwks(include_inactive=False)
    jwk = jwks.keys[0]
    payload = {
        "key": jwk.as_dict(),
        "iss": get_issuer(),
        "kid": jwk.kid,
        "alg": get_alg_for_key(jwk),
    }
    return payload


def get_client_jwks(client, kid=None):
    """Get the client JWK set, either stored locally or by downloading them from the URI the client indicated."""

    @cache.cached(timeout=50, key_prefix=f"jwks_{client.client_id}")
    def get_public_jwks():
        return httpx.get(client.jwks_uri).json()

    if client.jwks_uri:
        raw_jwks = get_public_jwks()
        key_set = jwk.KeySet.import_key_set(raw_jwks)
        key = key_set.get_by_kid(kid)
        return key

    if client.jwks:
        raw_jwks = json.loads(client.jwks)
        key_set = jwk.KeySet.import_key_set(raw_jwks)
        key = key_set.get_by_kid(kid)
        return key

    return None


class UserInfo(oidc_core.UserInfo):
    REGISTERED_CLAIMS = oidc_core.UserInfo.REGISTERED_CLAIMS + ["groups"]
    SCOPES_CLAIMS_MAPPING = {
        "groups": ["groups"],
        **oidc_core.UserInfo.SCOPES_CLAIMS_MAPPING,
    }


def make_address_claim(user):
    payload = {}
    mapping = {
        "formatted_address": "formatted",
        "street": "street_address",
        "locality": "locality",
        "region": "region",
        "postal_code": "postal_code",
    }
    for user_attr, claim in mapping.items():
        if val := getattr(user, user_attr):
            payload[claim] = val

    return payload


def generate_user_claims(user, jwt_mapping_config=None):
    jwt_mapping_config = {
        **(current_app.config["CANAILLE_OIDC"]["USERINFO_MAPPING"]),
        **(jwt_mapping_config or {}),
    }

    data = {}
    for claim in UserInfo.REGISTERED_CLAIMS:
        raw_claim = jwt_mapping_config.get(claim.upper())
        if raw_claim:
            formatted_claim = current_app.jinja_env.from_string(raw_claim).render(
                user=user
            )
            if formatted_claim:
                # According to https://openid.net/specs/openid-connect-core-1_0.html#UserInfoResponse
                # it's better to not insert a null or empty string value
                data[claim] = formatted_claim

        if claim == "address" and (address := make_address_claim(user)):
            data[claim] = address

        if claim == "groups" and user.groups:
            data[claim] = [group.display_name for group in user.groups]

        if claim == "updated_at":
            data[claim] = int(float(data[claim]))

    return data


def save_authorization_code(code, request):
    nonce = request.payload.data.get("nonce")
    now = datetime.datetime.now(datetime.timezone.utc)
    scope = request.client.get_allowed_scope(request.payload.scope)
    code = models.AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code=code,
        subject=request.user,
        client=request.client,
        redirect_uri=request.payload.redirect_uri or request.client.redirect_uris[0],
        scope=scope.split(" "),
        nonce=nonce,
        issue_date=now,
        lifetime=AUTHORIZATION_CODE_LIFETIME,
        challenge=request.payload.data.get("code_challenge"),
        challenge_method=request.payload.data.get("code_challenge_method"),
        auth_time=g.session.last_login_datetime,
    )
    Backend.instance.save(code)
    return code.code


class JWTClientAuth(rfc7523.JWTBearerClientAssertion):
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

        return jwk.as_dict()


class AuthorizationCodeGrant(rfc6749.AuthorizationCodeGrant):
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


class OpenIDCode(oidc_core.OpenIDCode):
    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_jwt_config(self, grant=None):
        # Hotfix until fixed upstream:
        # client.id_token_signed_response_alg should be used when defined,
        # this can only happen if 'alg' is not set
        # https://github.com/authlib/authlib/issues/806
        result = get_jwt_config(grant)
        del result["alg"]
        return result

    def generate_user_info(self, user, scope):
        return UserInfo(generate_user_claims(user)).filter(scope)

    def get_audiences(self, request):
        client = request.client
        return [aud.client_id for aud in client.audience]


class PasswordGrant(rfc6749.ResourceOwnerPasswordCredentialsGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = [
        "client_secret_basic",
        "client_secret_post",
        JWTClientAuth.CLIENT_AUTH_METHOD,
        "none",
    ]

    def authenticate_user(self, username, password):
        user = get_user_from_login(username)
        if not user:
            return None

        success, _ = Backend.instance.check_user_password(user, password)
        if not success:
            return None

        return user


class RefreshTokenGrant(rfc6749.RefreshTokenGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = [
        "client_secret_basic",
        "client_secret_post",
        JWTClientAuth.CLIENT_AUTH_METHOD,
        "none",
    ]

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


class JWTBearerGrant(rfc7523.JWTBearerGrant):
    def resolve_issuer_client(self, issuer):
        return Backend.instance.get(models.Client, client_id=issuer)

    def resolve_client_key(self, client, headers, payload):
        jwk = server_jwks().keys[0]
        return jwk.as_dict()

    def authenticate_user(self, subject: str):
        return get_user_from_login(subject)

    def has_granted_permission(self, client, user):
        grant = Backend.instance.get(models.Consent, client=client, subject=user)
        has_permission = (grant and not grant.revoked) or (not grant and client.trusted)
        return has_permission


class OpenIDImplicitGrant(oidc_core.OpenIDImplicitGrant):
    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_jwt_config(self, grant=None):
        # Hotfix until fixed upstream:
        # client.id_token_signed_response_alg should be used when defined,
        # this can only happen if 'alg' is not set
        # https://github.com/authlib/authlib/issues/806
        result = get_jwt_config(grant)
        del result["alg"]
        return result

    def generate_user_info(self, user, scope):
        return UserInfo(generate_user_claims(user)).filter(scope)

    def get_audiences(self, request):
        client = request.client
        return [aud.client_id for aud in client.audience]


class OpenIDHybridGrant(oidc_core.OpenIDHybridGrant):
    def save_authorization_code(self, code, request):
        return save_authorization_code(code, request)

    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_jwt_config(self, grant=None):
        # Hotfix until fixed upstream:
        # client.id_token_signed_response_alg should be used when defined,
        # this can only happen if 'alg' is not set
        # https://github.com/authlib/authlib/issues/806
        result = get_jwt_config(grant)
        del result["alg"]
        return result

    def generate_user_info(self, user, scope):
        return UserInfo(generate_user_claims(user)).filter(scope)

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


class BearerTokenValidator(rfc6750.BearerTokenValidator):
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


class RevocationEndpoint(rfc7009.RevocationEndpoint):
    def query_token(self, token, token_type_hint):
        return query_token(token, token_type_hint)

    def revoke_token(self, token, request):
        token.revokation_date = datetime.datetime.now(datetime.timezone.utc)
        Backend.instance.save(token)


class IntrospectionEndpoint(rfc7662.IntrospectionEndpoint):
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
        print(response)
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
        return server_jwks().keys[0].as_dict(private=False)

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

        if "scope" in kwargs:
            kwargs["scope"] = kwargs["scope"].split(" ")

        if "response_types" in kwargs:
            kwargs["response_types"] = list(
                {
                    item
                    for response_type in kwargs["response_types"]
                    for item in response_type.split(" ")
                }
            )

        return kwargs


class ClientRegistrationEndpoint(
    ClientManagementMixin, rfc7591.ClientRegistrationEndpoint
):
    software_statement_alg_values_supported = [
        "none",
        "RS256",
        "ES256",
        "HS256",
        "EdDSA",
    ]

    def generate_client_registration_info(self, client, request):
        payload = {
            "scope": " ".join(client.scope) if client.scope else "",
            "registration_client_uri": url_for(
                "oidc.endpoints.client_registration_management",
                client_id=client.client_id,
                _external=True,
            ),
        }

        if "Authorization" in request.headers:
            access_token = request.headers["Authorization"].split(" ")[1]
            payload["registration_access_token"] = access_token

        return payload

    def save_client(self, client_info, client_metadata, request):
        client = models.Client(
            # this won't be needed when OIDC RP Initiated Logout is
            # directly implemented in authlib:
            # https://gitlab.com/yaal/canaille/-/issues/157
            post_logout_redirect_uris=request.payload.data.get(
                "post_logout_redirect_uris"
            ),
            **self.client_convert_data(**client_info, **client_metadata),
        )
        Backend.instance.save(client)
        client.audience = [client]
        Backend.instance.save(client)
        return client


class ClientConfigurationEndpoint(
    ClientManagementMixin, rfc7592.ClientConfigurationEndpoint
):
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


class CodeChallenge(rfc7636.CodeChallenge):
    def get_authorization_code_challenge(self, authorization_code):
        return authorization_code.challenge

    def get_authorization_code_challenge_method(self, authorization_code):
        return authorization_code.challenge_method


class UserInfoEndpoint(oidc_core.UserInfoEndpoint):
    def get_issuer(self):
        return get_issuer()

    def generate_user_info(self, user, scope):
        return UserInfo(generate_user_claims(user)).filter(scope)

    def resolve_private_key(self):
        return server_jwks(include_inactive=False).as_dict()


class IssuerParameter(rfc9207.IssuerParameter):
    def get_issuer(self) -> str:
        return get_issuer()


class JWTAuthenticationRequest(rfc9101.JWTAuthenticationRequest):
    def resolve_client_public_key(self, client):
        return get_client_jwks(client).as_dict()

    def get_request_object(self, request_uri: str):
        return httpx.get(request_uri).text

    def get_server_metadata(self):
        return openid_configuration()

    def get_client_require_signed_request_object(self, client):
        return client.client_metadata.get("require_signed_request_object", False)


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
        "user_info": UserInfo(generate_user_claims(user)).filter(scope),
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

    oidc_config = app.config.get("CANAILLE_OIDC")
    if oidc_config and not oidc_config.get("ACTIVE_JWKS"):
        oidc_config["ACTIVE_JWKS"] = [
            make_default_jwk(app.config.get("SECRET_KEY")).as_dict()
        ]

    # hacky, but needed for tests as somehow the same 'authorization' object is used
    # between tests
    authorization.__init__()
    authorization.init_app(app, query_client=query_client, save_token=save_token)

    authorization.register_grant(rfc6749.ClientCredentialsGrant)
    authorization.register_grant(rfc6749.ImplicitGrant)
    authorization.register_grant(PasswordGrant)
    authorization.register_grant(RefreshTokenGrant)
    authorization.register_grant(JWTBearerGrant)
    authorization.register_grant(OpenIDImplicitGrant)
    authorization.register_grant(OpenIDHybridGrant)
    authorization.register_grant(
        AuthorizationCodeGrant,
        [
            OpenIDCode(require_nonce=app.config["CANAILLE_OIDC"]["REQUIRE_NONCE"]),
            CodeChallenge(required=True),
        ],
    )

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

    require_oauth.register_token_validator(BearerTokenValidator())

    authorization.register_endpoint(UserInfoEndpoint(resource_protector=require_oauth))
    authorization.register_endpoint(IntrospectionEndpoint)
    authorization.register_endpoint(RevocationEndpoint)
    authorization.register_endpoint(
        ClientRegistrationEndpoint(
            claims_classes=[
                rfc7591.ClientMetadataClaims,
                rfc9101.ClientMetadataClaims,
                oidc_registration.ClientMetadataClaims,
            ]
        )
    )
    authorization.register_endpoint(
        ClientConfigurationEndpoint(
            claims_classes=[
                rfc7591.ClientMetadataClaims,
                rfc9101.ClientMetadataClaims,
                oidc_registration.ClientMetadataClaims,
            ]
        )
    )

    authorization.register_extension(IssuerParameter())
    authorization.register_extension(JWTAuthenticationRequest())
