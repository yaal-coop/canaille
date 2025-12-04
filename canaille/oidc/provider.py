import datetime
import json
import uuid

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
from authlib.oauth2 import rfc9101
from authlib.oauth2 import rfc9207
from authlib.oauth2.rfc6749 import InvalidClientError
from authlib.oidc import core as oidc_core
from authlib.oidc import registration as oidc_registration
from authlib.oidc.core.grants.util import generate_id_token
from flask import current_app
from flask import g
from flask import request
from flask import url_for
from joserfc import jwt
from joserfc.errors import JoseError
from werkzeug.security import gen_salt

from canaille.app import models
from canaille.app.flask import cache
from canaille.backends import Backend
from canaille.core.auth import get_user_from_login

from .jose import build_client_management_token
from .jose import get_alg_for_key
from .jose import get_client_jwks
from .jose import make_default_okp_jwk
from .jose import registry
from .jose import server_jwks
from .userinfo import UserInfo
from .userinfo import generate_user_claims

AUTHORIZATION_CODE_LIFETIME = 84400
JWT_JTI_CACHE_LIFETIME = 3600

AMR_MAPPING = {
    "password": ["pwd"],
    "otp": ["otp"],
    "sms": ["sms", "mca"],
    "email": ["mca"],
}


def compute_amr_values(authentication_methods):
    """Convert internal authentication methods to AMR values (RFC 8176).

    Returns a list of AMR values, automatically adding 'mfa' if multiple
    factors were used.
    """
    if not authentication_methods:
        return None

    amr_values = []
    for method in authentication_methods:
        if method in AMR_MAPPING:
            amr_values.extend(AMR_MAPPING[method])

    amr_values = list(dict.fromkeys(amr_values))

    if len(authentication_methods) > 1:
        amr_values.append("mfa")

    return amr_values if amr_values else None


def get_bearer_token(request):
    """Get the Bearer token from the request headers."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return None

    return auth_header.split()[1]


def exists_nonce(nonce, request):
    client = Backend.instance.get(models.Client, id=request.payload.client_id)
    exists = Backend.instance.query(
        models.AuthorizationCode, client=client, nonce=nonce
    )
    return bool(exists)


def get_issuer():
    if server_name := current_app.config.get("SERVER_NAME"):
        scheme = current_app.config.get("PREFERRED_URL_SCHEME", "http")
        return f"{scheme}://{server_name}"

    return request.url_root


def get_jwt_config(grant=None):
    jwks = server_jwks(include_inactive=False)

    jwk = None
    if (grant and hasattr(grant, "request") and grant.request.client) and (
        alg := grant.request.client.id_token_signed_response_alg
    ):
        jwk = jwks.pick_random_key(alg)

    if jwk is None:
        jwk = jwks.keys[0]

    payload = {
        "key": jwk.as_dict(),
        "iss": get_issuer(),
        "kid": jwk.kid,
        "alg": get_alg_for_key(jwk),
    }
    return payload


def save_authorization_code(code, request):
    nonce = request.payload.data.get("nonce")
    now = datetime.datetime.now(datetime.timezone.utc)
    scope = request.client.get_allowed_scope(request.payload.scope)
    authentication_methods = (
        g.session.authentication_methods
        if hasattr(g, "session") and g.session
        else None
    )
    amr = compute_amr_values(authentication_methods)
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
        amr=amr,
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
    INCLUDE_NEW_REFRESH_TOKEN = True

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
        return response


class ClientManagementMixin:
    def _validate_jwt_claims(self, claims):
        """Validate common JWT claims for client registration/management.

        Returns True if claims are valid, None otherwise.
        This method validates common claims. Subclasses should override this
        to add specific validation logic and call super()._validate_jwt_claims().
        """
        now = datetime.datetime.now(datetime.timezone.utc)

        if claims.get("exp") and claims["exp"] < now.timestamp():
            return None

        issuer = get_issuer()
        if claims.get("iss") != issuer or claims.get("aud") != issuer:
            return None

        return True

    def authenticate_token(self, request):
        """Authenticate JWT tokens for dynamic client registration.

        Returns True if authentication succeeds, None if it fails.
        Stores the validated JWT claims in request.jwt_claims for later use.
        """
        if not (bearer_token := get_bearer_token(request)):
            if current_app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_OPEN"]:
                return True
            return None

        jwks = server_jwks(include_inactive=True)
        try:
            decoded = jwt.decode(bearer_token, jwks.keys[0], registry=registry)
        except (JoseError, ValueError, KeyError):
            return None

        if not self._validate_jwt_claims(decoded.claims):
            return None

        request.jwt_claims = decoded.claims
        return True

    def get_server_metadata(self):
        from .metadata import openid_configuration

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

    def _validate_jwt_claims(self, claims):
        """Validate JWT claims for client registration.

        Returns True if claims are valid, None otherwise.
        """
        if not super()._validate_jwt_claims(claims):
            return None

        scope = claims.get("scope")
        if scope != "client:register":
            return None

        client_id = claims.get("sub")
        existing_client = Backend.instance.get(models.Client, client_id=client_id)
        if existing_client:
            return None

        return True

    def generate_client_registration_info(self, client, request):
        payload = {
            "scope": " ".join(client.scope) if client.scope else "",
            "registration_client_uri": url_for(
                "oidc.endpoints.client_registration_management",
                client_id=client.client_id,
                _external=True,
            ),
            "registration_access_token": build_client_management_token(
                "client:manage", client_id=client.client_id
            ),
        }
        return payload

    def generate_client_id(self, request):
        """Generate client_id for new client registration.

        Read the value from the value passed in the JWT if present,
        create a random value if there is not authentication.
        """
        return (
            request.jwt_claims.get("sub")
            if hasattr(request, "jwt_claims")
            else str(uuid.uuid4())
        )

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

        current_app.logger.security(
            f"OIDC Dynamic Client Creation of {client.client_id}"
        )
        return client


class ClientConfigurationEndpoint(
    ClientManagementMixin, rfc7592.ClientConfigurationEndpoint
):
    def _validate_jwt_claims(self, claims):
        """Validate JWT claims for client management.

        Returns True if claims are valid, None otherwise.
        """
        if not super()._validate_jwt_claims(claims):
            return None

        scope = claims.get("scope")
        if scope != "client:manage":
            return None

        client_id = claims.get("sub")
        if not Backend.instance.get(models.Client, client_id=client_id):
            return None

        return True

    def authenticate_client(self, request):
        client_id = request.uri.split("/")[-1]
        return Backend.instance.get(models.Client, client_id=client_id)

    def revoke_access_token(self, request, token):
        pass

    def check_permission(self, client, request):
        return True

    def delete_client(self, client, request):
        current_app.logger.security(
            f"OIDC Dynamic Client deletion of {client.client_id}"
        )
        Backend.instance.delete(client)

    def update_client(self, client, client_metadata, request):
        Backend.instance.update(client, **self.client_convert_data(**client_metadata))
        Backend.instance.save(client)

        current_app.logger.security(f"OIDC Dynamic Client update of {client.client_id}")
        return client

    def generate_client_registration_info(self, client, request):
        access_token = get_bearer_token(request)
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
        from .metadata import openid_configuration

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
        "canaille.oidc.provider.generate_access_token"
    )

    oidc_config = app.config.get("CANAILLE_OIDC")
    if oidc_config and not oidc_config.get("ACTIVE_JWKS"):
        oidc_config["ACTIVE_JWKS"] = [
            make_default_okp_jwk(app.config.get("SECRET_KEY")).as_dict()
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
