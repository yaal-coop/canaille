import datetime
import json
import time
import uuid

from authlib import oauth2
from authlib.integrations.flask_oauth2 import AuthorizationServer
from authlib.integrations.flask_oauth2 import ResourceProtector
from authlib.oauth2 import form_post
from authlib.oauth2 import multiple_response_types
from authlib.oauth2 import rfc6749
from authlib.oauth2 import rfc6750
from authlib.oauth2 import rfc7009
from authlib.oauth2 import rfc7523
from authlib.oauth2 import rfc7591
from authlib.oauth2 import rfc7592
from authlib.oauth2 import rfc7636
from authlib.oauth2 import rfc7662
from authlib.oauth2 import rfc8628
from authlib.oauth2 import rfc9068
from authlib.oauth2 import rfc9101
from authlib.oauth2 import rfc9207
from authlib.oauth2 import rfc9470
from authlib.oauth2.rfc6749 import AccessDeniedError
from authlib.oauth2.rfc6749 import InvalidClientError
from authlib.oauth2.rfc6749 import InvalidGrantError
from authlib.oauth2.rfc6749 import InvalidScopeError
from authlib.oauth2.rfc6749 import OAuth2Response
from authlib.oauth2.rfc6749 import UnauthorizedClientError
from authlib.oauth2.rfc7591 import InvalidClientMetadataError
from authlib.oauth2.rfc9101.errors import InvalidRequestObjectError
from authlib.oidc import backchannel
from authlib.oidc import core as oidc_core
from authlib.oidc import prompt_create
from authlib.oidc import registration as oidc_registration
from authlib.oidc import rpinitiated
from authlib.oidc.core.authorization_request import OpenIDJWTAuthenticationRequest
from flask import current_app
from flask import g
from flask import request
from flask import url_for
from joserfc.jwk import OctKey
from werkzeug.security import gen_salt

from canaille.app import models
from canaille.app.flask import cache
from canaille.app.session import logout_user
from canaille.app.templating import render_template
from canaille.backends import Backend
from canaille.core.auth import get_user_from_login
from canaille.oidc.models import OWNED_CLIENT_FORBIDDEN_GRANT_TYPES
from canaille.oidc.utils import fetch_document
from canaille.oidc.utils import is_trusted_domain
from canaille.oidc.utils import prompt_values_supported
from canaille.scim import scim_base_url

from .jose import SYMMETRIC_ALGORITHMS
from .jose import build_client_management_token
from .jose import client_secret_key
from .jose import decode_server_token
from .jose import get_alg_for_key
from .jose import get_client_jwks
from .jose import make_default_okp_jwk
from .jose import make_default_rsa_jwk
from .jose import server_jwks
from .userinfo import UserInfo
from .userinfo import generate_user_claims
from .utils import unique_scopes

AUTHORIZATION_CODE_LIFETIME = 60
JWT_JTI_CACHE_LIFETIME = 3600
JWT_BEARER_ASSERTION_MAX_LIFETIME = 3600

AMR_MAPPING = {
    "password": ["pwd"],
    "otp": ["otp"],
    "sms": ["sms", "mca"],
    "email": ["mca"],
    "fido2": ["hwk"],
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


def _get_signing_key(client):
    """Select the signing key and algorithm for the given client."""
    jwks = server_jwks(include_inactive=False)
    jwk = None
    alg = None
    if client and (alg := client.id_token_signed_response_alg):
        jwk = jwks.pick_random_key(alg)

    if jwk is None:
        alg = None
        jwk = jwks.pick_random_key("RS256")

    if jwk is None:
        jwk = jwks.keys[0]

    return jwk, alg or get_alg_for_key(jwk)


def current_sid():
    """Return the identifier of the session of the current user, or None."""
    return g.session.sid if g.get("session") else None


def token_sid(request):
    """Return the identifier of the session where a token is issued.

    Tokens issued at the token endpoint inherit the session of their code or
    of their refresh token. Tokens issued at the authorization endpoint, in the
    implicit and hybrid flows, belong to the current session.
    """
    if request.authorization_code:
        return request.authorization_code.sid

    if request.refresh_token:
        return request.refresh_token.sid

    if request.payload.response_type:
        return current_sid()

    return None


def save_authorization_code(code, request):
    nonce = request.payload.data.get("nonce")
    now = datetime.datetime.now(datetime.UTC)
    scope = request.client.get_allowed_scope(request.payload.scope)
    code = models.AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code=code,
        subject=request.user,
        client=request.client,
        redirect_uri=request.payload.redirect_uri or request.client.redirect_uris[0],
        scope=unique_scopes(scope),
        nonce=nonce,
        issue_date=now,
        lifetime=AUTHORIZATION_CODE_LIFETIME,
        challenge=request.payload.data.get("code_challenge"),
        challenge_method=request.payload.data.get("code_challenge_method"),
        auth_time=datetime.datetime.fromtimestamp(request.auth_time, datetime.UTC)
        if request.auth_time is not None
        else None,
        acr=request.acr,
        amr=request.amr,
        sid=current_sid(),
    )
    Backend.instance.save(code)
    return code.code


class JWTClientAuth(rfc7523.JWTBearerClientAssertion):
    def __call__(self, query_client, request):
        """Authenticate no client without SERVER_NAME, as the audience could not be checked."""
        if not current_app.config["SERVER_NAME"]:
            return None

        return super().__call__(query_client, request)

    def get_audiences(self):
        """RFC 7523 §3 uses the token endpoint, and RFC 10070 the issuer."""
        return [url_for("oidc.endpoints.issue_token", _external=True), get_issuer()]

    def validate_jti(self, claims, jti):
        """Indicate whether the jti was used before."""
        key = "jti:{}-{}".format(claims["sub"], jti)
        if cache.get(key):
            return False
        cache.set(key, 1, timeout=JWT_JTI_CACHE_LIFETIME)
        return True

    def resolve_client_public_key(self, client):
        """Per OIDC Core §9, client_secret_jwt assertions are signed with the client secret."""
        # Workaround: authlib handles client_secret_jwt and private_key_jwt as one
        # "client_assertion_jwt" method, so the key depends on the registered method.
        if client.token_endpoint_auth_method == "client_secret_jwt":
            key = client_secret_key(client)
            if not key:
                raise InvalidClientError()

            return key

        jwk = get_client_jwks(client)
        if not jwk:
            raise InvalidClientError(description="No matching JWK")

        return jwk


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
        if not authorization_code.subject or authorization_code.subject.locked:
            return None

        if not authorization_code.client.is_usable_by(authorization_code.subject):
            raise InvalidGrantError("The user cannot use this client.")

        return authorization_code.subject


class ClientCredentialsGrant(rfc6749.ClientCredentialsGrant):
    """Per RFC 6749 §4.4, only confidential clients can use this grant."""

    TOKEN_ENDPOINT_AUTH_METHODS = [
        "client_secret_basic",
        "client_secret_post",
        JWTClientAuth.CLIENT_AUTH_METHOD,
    ]


class AuthorizationSession(
    oauth2.AuthorizationSession, oidc_core.AuthorizationSessionMixin
):
    """Give authlib the state of the user session during an authorization request."""

    def get_interaction_time(self, request, interaction):
        if interaction == "login":
            login_datetime = g.session and g.session.last_login_datetime
            return login_datetime.timestamp() if login_datetime else None

        if interaction == "select_account":
            selection_datetime = g.session and g.session.account_selection_datetime
            return selection_datetime.timestamp() if selection_datetime else None

        if interaction == "consent":
            consent = get_consent(request.client, request.user)
            if consent and not consent.revoked and consent.issue_date:
                return consent.issue_date.timestamp()

        return None

    def is_consent_needed(self, request):
        consent = get_consent(request.client, request.user)
        if consent and consent.revoked:
            return True

        if request.client.trusted:
            return False

        if not consent:
            return True

        requested_scopes = request.payload.scope or ""
        allowed_scopes = unique_scopes(
            request.client.get_allowed_scope(requested_scopes)
        )
        return not set(allowed_scopes).issubset(consent.scope)

    def get_amr(self):
        return compute_amr_values(
            g.session.authentication_methods if g.session else None
        )

    def can_redirect_error(self, request, error):
        """Redirect the errors to the clients that the user can use only."""
        if not self.user or not request.client:
            return True

        return request.client.is_usable_by(self.user)


class PromptValues(prompt_create.PromptValues):
    """Refuse the prompt values that Canaille does not support."""

    def get_server_metadata(self):
        return {"prompt_values_supported": prompt_values_supported()}


def get_consent(client, user):
    """Return the consent of a user for a client, or None."""
    consents = Backend.instance.query(models.Consent, client=client, subject=user)
    return consents[0] if consents else None


class OIDCGrantMixin:
    """Shared implementation of the authlib JWT config API for OIDC grants."""

    def resolve_client_private_key(self, client):
        jwk, _ = _get_signing_key(client)
        return jwk

    def get_client_algorithm(self, client):
        _, alg = _get_signing_key(client)
        return alg

    def get_client_claims(self, client):
        """Per OIDC Core §2, a single audience is sent as a string."""
        audience = [aud.client_id for aud in client.full_audience]
        return {
            "iss": get_issuer(),
            "aud": audience[0] if len(audience) == 1 else audience,
        }

    def get_encode_header(self, client):
        jwk, alg = _get_signing_key(client)
        return {"alg": alg, "kid": jwk.kid}


class OpenIDCode(OIDCGrantMixin, oidc_core.OpenIDCode):
    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_authorization_code_claims(self, authorization_code):
        claims = super().get_authorization_code_claims(authorization_code)
        if authorization_code.sid:
            claims["sid"] = authorization_code.sid
        return claims

    def generate_user_info(self, user, scope, claims):
        return UserInfo(generate_user_claims(user)).filter(scope, claims)


class PasswordGrant(rfc6749.ResourceOwnerPasswordCredentialsGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = [
        "client_secret_basic",
        "client_secret_post",
        JWTClientAuth.CLIENT_AUTH_METHOD,
        "none",
    ]

    def authenticate_token_endpoint_client(self):
        self.request.client = super().authenticate_token_endpoint_client()
        return self.request.client

    def authenticate_user(self, username, password):
        """Return the user if they can use the client and the password is right.

        Both failures give the same error, so the endpoint cannot check passwords
        of users who cannot use the client.
        """
        user = get_user_from_login(username)
        if not user or not self.request.client.is_usable_by(user):
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
        if not credential.subject or credential.subject.locked:
            return None

        if not credential.client.is_usable_by(credential.subject):
            raise InvalidGrantError("The user cannot use this client.")

        return credential.subject

    def revoke_old_credential(self, credential):
        credential.revokation_date = datetime.datetime.now(datetime.UTC)
        Backend.instance.save(credential)


class JWTBearerGrant(rfc7523.JWTBearerGrant):
    """Per RFC 7523 §3, the client in the 'iss' claim signs the assertion.

    The assertion must name a user, and can only be used once.
    """

    CLAIMS_OPTIONS = {
        **rfc7523.JWTBearerGrant.CLAIMS_OPTIONS,
        "sub": {"essential": True},
        "jti": {"essential": True},
    }

    def verify_claims(self, claims):
        super().verify_claims(claims)
        if isinstance(claims["aud"], list) and len(claims["aud"]) > 1:
            raise InvalidGrantError(
                description="The 'aud' claim must have a single value."
            )

        # Per RFC 7523 §3, an exp too far in the future can be refused.
        if claims["exp"] - time.time() > JWT_BEARER_ASSERTION_MAX_LIFETIME:
            raise InvalidGrantError(description="The assertion expires too late.")

        key = "jwt-bearer-jti:{}-{}".format(claims["iss"], claims["jti"])
        if cache.get(key):
            raise InvalidGrantError(description="The assertion was already used.")
        cache.set(key, 1, timeout=JWT_BEARER_ASSERTION_MAX_LIFETIME + self.LEEWAY)

    def resolve_issuer_client(self, issuer):
        return Backend.instance.get(models.Client, client_id=issuer)

    def resolve_client_public_key(self, client):
        key_set = get_client_jwks(client)
        if not key_set:
            raise InvalidGrantError(description="The client has no public key.")

        return key_set

    def get_audiences(self):
        """RFC 7523 §3 uses the token endpoint, and draft-ietf-oauth-rfc7523bis the issuer."""
        return [url_for("oidc.endpoints.issue_token", _external=True), get_issuer()]

    def authenticate_user(self, subject: str):
        user = get_user_from_login(subject)
        if not user or user.locked:
            return None

        if not self.request.client.is_usable_by(user):
            raise InvalidGrantError("The user cannot use this client.")

        return user

    def has_granted_permission(self, client, user):
        """Check that the user consented to the requested scopes, or that the client is trusted."""
        consent = get_consent(client, user)
        if consent and consent.revoked:
            return False

        if client.trusted:
            return True

        if not consent:
            return False

        requested_scopes = unique_scopes(
            client.get_allowed_scope(self.request.payload.scope or "")
        )
        return set(requested_scopes).issubset(consent.scope)


class SessionClaimMixin:
    """Put the session identifier in the ID tokens of the authorization endpoint."""

    def get_compatible_claims(self, request):
        claims = super().get_compatible_claims(request)
        if sid := current_sid():
            claims["sid"] = sid
        return claims


class OpenIDImplicitGrant(
    SessionClaimMixin, OIDCGrantMixin, oidc_core.OpenIDImplicitGrant
):
    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def generate_user_info(self, user, scope, claims):
        return UserInfo(generate_user_claims(user)).filter(scope, claims)


class OpenIDHybridGrant(SessionClaimMixin, OIDCGrantMixin, oidc_core.OpenIDHybridGrant):
    def save_authorization_code(self, code, request):
        return save_authorization_code(code, request)

    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def generate_user_info(self, user, scope, claims):
        return UserInfo(generate_user_claims(user)).filter(scope, claims)


class DeviceAuthorizationEndpoint(rfc8628.DeviceAuthorizationEndpoint):
    """Issue a device code, a user code and a verification URI for a device (RFC 8628)."""

    CLIENT_AUTH_METHODS = [
        "client_secret_basic",
        "client_secret_post",
        JWTClientAuth.CLIENT_AUTH_METHOD,
        "none",
    ]

    @property
    def EXPIRES_IN(self):
        lifetime = current_app.config["CANAILLE_OIDC"]["DEVICE_CODE_LIFETIME"]
        return int(lifetime.total_seconds())

    @property
    def INTERVAL(self):
        interval = current_app.config["CANAILLE_OIDC"]["DEVICE_CODE_POLLING_INTERVAL"]
        return int(interval.total_seconds())

    @property
    def USER_CODE_TYPE(self):
        return current_app.config["CANAILLE_OIDC"]["DEVICE_USER_CODE_TYPE"]

    def authenticate_client(self, request):
        client = super().authenticate_client(request)
        if not client.check_grant_type(rfc8628.DEVICE_CODE_GRANT_TYPE):
            raise UnauthorizedClientError(
                description="The client cannot use the device authorization grant."
            )
        return client

    def generate_user_code(self):
        """Generate a user code that no other active device code uses."""
        while True:
            user_code = super().generate_user_code()
            codes = Backend.instance.query(models.DeviceCode, user_code=user_code)
            if all(code.is_expired() for code in codes):
                return user_code

    def get_verification_uri(self):
        return url_for("oidc.endpoints.device", _external=True)

    def save_device_credential(self, client_id, scope, data):
        client = Backend.instance.get(models.Client, client_id=client_id)
        allowed_scope = client.get_allowed_scope(scope)
        if scope and not allowed_scope:
            raise InvalidScopeError()

        device_code = models.DeviceCode(
            device_code_id=gen_salt(48),
            device_code=data["device_code"],
            user_code=data["user_code"],
            client=client,
            scope=allowed_scope.split(),
            status="pending",
            issue_date=datetime.datetime.now(datetime.UTC),
            lifetime=data["expires_in"],
        )
        Backend.instance.save(device_code)


class DeviceCodeGrant(rfc8628.DeviceCodeGrant):
    """Exchange a device code for a token at the token endpoint, once the user approved it (RFC 8628)."""

    TOKEN_ENDPOINT_AUTH_METHODS = [
        "client_secret_basic",
        "client_secret_post",
        JWTClientAuth.CLIENT_AUTH_METHOD,
        "none",
    ]

    def query_device_credential(self, device_code):
        return Backend.instance.get(models.DeviceCode, device_code=device_code)

    def validate_device_credential(self, credential):
        """Read the user decision on the device code itself.

        The parent class reads it again by ``user_code``, which is not unique.
        """
        if credential.is_expired():
            raise rfc8628.ExpiredTokenError()

        if credential.status == "denied":
            Backend.instance.delete(credential)
            raise AccessDeniedError()

        if credential.status == "authorized":
            return self.authenticate_device_user(credential)

        if self.should_slow_down(credential):
            raise rfc8628.SlowDownError()

        raise rfc8628.AuthorizationPendingError()

    def authenticate_device_user(self, credential):
        """Check that the user who approved the device can still use the client.

        The device code cannot be used anymore when the check fails.
        """
        if not credential.subject or credential.subject.locked:
            Backend.instance.delete(credential)
            raise InvalidGrantError("There is no 'user' for this code.")

        if not credential.client.is_usable_by(credential.subject):
            Backend.instance.delete(credential)
            raise InvalidGrantError("The user cannot use this client.")

        return credential.subject

    def should_slow_down(self, credential):
        now = datetime.datetime.now(datetime.UTC)
        interval = current_app.config["CANAILLE_OIDC"]["DEVICE_CODE_POLLING_INTERVAL"]
        last_polled = credential.last_polled
        credential.last_polled = now
        Backend.instance.save(credential)
        return last_polled is not None and (now - last_polled) < interval

    def create_token_response(self):
        # The device_code is single use: drop it once a token has been issued.
        response = super().create_token_response()
        Backend.instance.delete(self.request.credential)
        return response


def query_client(client_id):
    return Backend.instance.get(models.Client, client_id=client_id)


def save_token(token, request):
    now = datetime.datetime.now(datetime.UTC)
    scope = unique_scopes(token.get("scope"))
    t = models.Token(
        token_id=gen_salt(48),
        type=token["token_type"],
        access_token=token["access_token"],
        issue_date=now,
        lifetime=token["expires_in"],
        scope=scope,
        client=request.client,
        refresh_token=token.get("refresh_token"),
        subject=request.user,
        audience=request.client.audience,
        sid=token_sid(request),
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
    CLIENT_AUTH_METHODS = [
        "client_secret_basic",
        "client_secret_post",
        JWTClientAuth.CLIENT_AUTH_METHOD,
    ]

    def query_token(self, token, token_type_hint):
        return query_token(token, token_type_hint)

    def revoke_token(self, token, request):
        token.revokation_date = datetime.datetime.now(datetime.UTC)
        Backend.instance.save(token)


class IntrospectedRefreshToken:
    """A token found by its refresh token, with the expiration of the refresh token."""

    def __init__(self, token):
        self.token = token

    def __getattr__(self, name):
        return getattr(self.token, name)

    def is_expired(self):
        return self.token.refresh_token_expire_date < datetime.datetime.now(
            datetime.UTC
        )

    def get_expires_at(self):
        return self.token.refresh_token_expire_date.timestamp()


class IntrospectionEndpoint(rfc7662.IntrospectionEndpoint):
    CLIENT_AUTH_METHODS = [
        "client_secret_basic",
        "client_secret_post",
        JWTClientAuth.CLIENT_AUTH_METHOD,
    ]

    def query_token(self, token, token_type_hint):
        item = query_token(token, token_type_hint)
        if item and item.refresh_token == token:
            return IntrospectedRefreshToken(item)

        return item

    def check_permission(self, token, client, request):
        return client in token.full_audience

    def introspect_token(self, token):
        response = {
            "active": True,
            "client_id": token.client.client_id,
            "token_type": token.type,
            "scope": token.get_scope(),
            "aud": access_token_audiences(
                token.client, token.audience, token.get_scope()
            ),
            "iss": get_issuer(),
            "exp": token.get_expires_at(),
            "iat": token.get_issued_at(),
        }
        if token.subject:
            response["username"] = token.subject.formatted_name
            response["sub"] = generate_user_claims(token.subject).get("sub")
        return response


class RegistrationAccessToken:
    """A registration access token validated by :class:`ClientManagementMixin`."""

    def __init__(self, claims):
        self.claims = claims

    def check_client(self, client):
        return self.claims.get("sub") == client.client_id


class ClientManagementMixin:
    def _validate_jwt_claims(self, claims):
        """Validate common JWT claims for client registration/management.

        Returns True if claims are valid, None otherwise.
        This method validates common claims. Subclasses should override this
        to add specific validation logic and call super()._validate_jwt_claims().
        """
        now = datetime.datetime.now(datetime.UTC)

        if claims.get("exp") and claims["exp"] < now.timestamp():
            return None

        issuer = get_issuer()
        if claims.get("iss") != issuer or claims.get("aud") != issuer:
            return None

        return True

    def authenticate_token(self, request):
        """Authenticate JWT tokens for dynamic client registration.

        Returns the token if authentication succeeds, None if it fails.
        Stores the validated JWT claims in request.jwt_claims for later use.
        """
        if not (bearer_token := get_bearer_token(request)):
            return None

        if not (decoded := decode_server_token(bearer_token)):
            return None

        if not self._validate_jwt_claims(decoded.claims):
            return None

        request.jwt_claims = decoded.claims
        return RegistrationAccessToken(decoded.claims)

    def get_server_metadata(self):
        from .metadata import openid_configuration

        result = openid_configuration()
        return result

    def extract_client_metadata(self, request):
        """Refuse the grants that issue tokens without a user consent.

        On updates, clients keep the grants that they already have.
        """
        client_metadata = super().extract_client_metadata(request)
        client = getattr(request, "client", None)
        kept = set(client.grant_types or []) if client else set()
        added = set(client_metadata.get("grant_types") or []) - kept
        if forbidden := added & OWNED_CLIENT_FORBIDDEN_GRANT_TYPES:
            raise InvalidClientMetadataError(
                f"Grant types not allowed: {', '.join(sorted(forbidden))}."
            )
        return client_metadata

    def resolve_public_key(self, request):
        return server_jwks().keys[0]

    def client_convert_data(self, **kwargs):
        if "client_id_issued_at" in kwargs:
            kwargs["client_id_issued_at"] = datetime.datetime.fromtimestamp(
                kwargs["client_id_issued_at"], datetime.UTC
            )

        # RFC7591 uses 0 to tell that the secret never expires, and not the epoch.
        if "client_secret_expires_at" in kwargs:
            kwargs["client_secret_expires_at"] = (
                datetime.datetime.fromtimestamp(
                    kwargs["client_secret_expires_at"], datetime.UTC
                )
                if kwargs["client_secret_expires_at"]
                else None
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

    def authenticate_token(self, request):
        """Allow client registration without a token when it is open.

        This only applies to the registration endpoint: :rfc:`7592` requests
        always need the registration access token issued to the client.
        """
        if (
            not get_bearer_token(request)
            and current_app.config["CANAILLE_OIDC"]["DYNAMIC_CLIENT_REGISTRATION_OPEN"]
        ):
            return True

        return super().authenticate_token(request)

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
            **self.client_convert_data(**client_info, **client_metadata),
        )
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
        """Allow the request, as the token already checks its client."""
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

    def generate_user_info(self, user, scope, claims):
        return UserInfo(generate_user_claims(user)).filter(scope, claims)

    def resolve_private_key(self):
        return server_jwks(include_inactive=False)


class EndSessionEndpoint(rpinitiated.EndSessionEndpoint):
    def get_server_jwks(self):
        return server_jwks(include_inactive=True)

    def end_session(self, end_session_request):
        logout_user()

    def is_post_logout_redirect_uri_legitimate(
        self,
        request,
        post_logout_redirect_uri,
        client,
        logout_hint,
    ):
        return is_trusted_domain(post_logout_redirect_uri)


class IssuerParameter(rfc9207.IssuerParameter):
    def get_issuer(self) -> str:
        return get_issuer()


RESPONSE_MODES_SUPPORTED = ["query", "fragment", "form_post"]


class MultipleResponseTypes(multiple_response_types.MultipleResponseTypes):
    def get_server_metadata(self):
        return {"response_modes_supported": list(RESPONSE_MODES_SUPPORTED)}


class FormPost(form_post.FormPost):
    """Send the authorization response with a Canaille page.

    The authlib page submits its form with an inline script,
    which the content security policy blocks.
    """

    def encode(self, response):
        authlib_response = super().encode(response)
        body = render_template(
            "oidc/form_post.html",
            redirect_uri=response.redirect_uri,
            params=response.params,
        )
        return OAuth2Response(
            authlib_response.status_code, body, authlib_response.headers
        )


class JWTAuthenticationRequest(OpenIDJWTAuthenticationRequest):
    def resolve_client_secret(self, client):
        """Per OIDC Core §10.1, symmetric signatures use the client secret.

        Only clients that registered a symmetric algorithm can use it.
        """
        if client.request_object_signing_alg not in SYMMETRIC_ALGORITHMS:
            return None

        return client.client_secret if client.has_usable_secret() else None

    def resolve_client_public_key(self, client):
        # Workaround: authlib 1.9 does not call resolve_client_secret
        # for symmetric signatures.
        if client.request_object_signing_alg in SYMMETRIC_ALGORITHMS:
            secret = self.resolve_client_secret(client)
            if not secret:
                raise InvalidRequestObjectError()

            return OctKey.import_key(secret)

        jwk = get_client_jwks(client)
        if not jwk and (client.jwks or client.jwks_uri):
            raise InvalidRequestObjectError(description="No matching JWK")

        return jwk

    def get_client_request_uris(self, client):
        return client.request_uris or []

    def validate_request_uri(self, request_uri: str, client):
        """Only download request objects at URIs the client registered."""
        return request_uri in (client.request_uris or [])

    def get_request_object(self, request_uri: str):
        """Download the request object at the URI passed in the authorization request.

        Errors are turned into a ``None``, that authlib renders as an
        ``invalid_request_uri`` error. The URI is unvalidated user input, so no
        exception must escape and turn into a HTTP 500.
        """
        try:
            return fetch_document(request_uri)
        except Exception:
            current_app.logger.debug(
                "could not download the request object at %s", request_uri
            )
            return None

    def get_server_metadata(self):
        from .metadata import openid_configuration

        return openid_configuration()

    def get_client_require_signed_request_object(self, client):
        return client.client_metadata.get("require_signed_request_object", False)


authorization = AuthorizationServer()
require_oauth = ResourceProtector()


def access_token_audiences(client, audience, scope):
    """Return the Canaille resources of the scope, and the other clients of ``audience``.

    Per RFC 9068 §3, the audiences are the resources that accept the token.
    The client itself is not an audience, so the access token cannot be
    used as an ID token.
    """
    scopes = unique_scopes(scope)
    audiences = []
    if "openid" in scopes:
        audiences.append(url_for("oidc.endpoints.userinfo", _external=True))

    if current_app.features.has_scim_server and any(
        scope_part.startswith("scim:") for scope_part in scopes
    ):
        audiences.append(scim_base_url())

    audiences.extend(other.client_id for other in audience or [] if other != client)
    return audiences or [get_issuer()]


class JWTAccessTokenGenerator(rfc9068.JWTBearerTokenGenerator):
    """Per RFC 9068, access tokens are JWTs that resource servers can verify."""

    def get_jwks(self):
        return server_jwks(include_inactive=False)

    def get_audiences(self, client, user, scope):
        return access_token_audiences(client, client.audience, scope)

    def get_extra_claims(self, client, grant_type, user, scope):
        if not user:
            return {}

        claims = generate_user_claims(user)
        user_info = UserInfo(claims).filter(scope)
        # Without the openid scope, the filtered claims have no 'sub'.
        if sub := claims.get("sub"):
            user_info["sub"] = sub
        return user_info


def generate_access_token(client, grant_type, user, scope, expires_in):
    if current_app.config["CANAILLE_OIDC"]["ACCESS_TOKEN_TYPE"] == "plain":
        return gen_salt(48)

    # Per RFC 9068 §4, resource servers must support RS256.
    jwks = server_jwks(include_inactive=False)
    alg = "RS256" if jwks.pick_random_key("RS256") else _get_signing_key(None)[1]
    generator = JWTAccessTokenGenerator(issuer=get_issuer(), alg=alg)
    return generator.access_token_generator(client, grant_type, user, scope, expires_in)


def access_token_lifetime(client, grant_type):
    lifetime = current_app.config["CANAILLE_OIDC"]["ACCESS_TOKEN_LIFETIME"]
    return int(lifetime.total_seconds())


def setup_oauth(app):
    app.config["OAUTH2_REFRESH_TOKEN_GENERATOR"] = True
    app.config["OAUTH2_ACCESS_TOKEN_GENERATOR"] = (
        "canaille.oidc.provider.generate_access_token"
    )
    app.config["OAUTH2_TOKEN_EXPIRES_IN"] = (
        "canaille.oidc.provider.access_token_lifetime"
    )

    oidc_config = app.config.get("CANAILLE_OIDC")
    if oidc_config and not oidc_config.get("ACTIVE_JWKS"):
        if not app.debug:
            app.logger.warning(
                "ACTIVE_JWKS is not configured. "
                "Please generate one or several keys, including at least one RSA key. "
                "https://canaille.readthedocs.io/en/latest/howtos/sso.html#server-key-management"
            )

        app.extensions["canaille_oidc_jwks_autogenerated"] = True
        oidc_config["ACTIVE_JWKS"] = [
            make_default_okp_jwk(app.config.get("SECRET_KEY")).as_dict(private=True),
            make_default_rsa_jwk().as_dict(private=True),
        ]

    # hacky, but needed for tests as somehow the same 'authorization' object is used
    # between tests
    authorization.__init__()
    authorization.init_app(app, query_client=query_client, save_token=save_token)

    authorization.register_grant(ClientCredentialsGrant)
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
            CodeChallenge(),
        ],
    )
    authorization.register_grant(DeviceCodeGrant)

    with app.app_context():
        if not app.config["SERVER_NAME"]:
            app.logger.warning(
                "The 'SERVER_NAME' configuration parameter is unset. JWT client authentication is disabled."
            )

    authorization.register_client_auth_method(
        JWTClientAuth.CLIENT_AUTH_METHOD,
        JWTClientAuth(),
    )

    require_oauth.register_token_validator(BearerTokenValidator())

    authorization.register_endpoint(UserInfoEndpoint(resource_protector=require_oauth))
    authorization.register_endpoint(DeviceAuthorizationEndpoint)
    authorization.register_endpoint(IntrospectionEndpoint)
    authorization.register_endpoint(RevocationEndpoint)
    authorization.register_endpoint(EndSessionEndpoint)
    authorization.register_endpoint(
        ClientRegistrationEndpoint(
            claims_classes=[
                rfc7591.ClientMetadataClaims,
                rfc9101.ClientMetadataClaims,
                oidc_registration.ClientMetadataClaims,
                rpinitiated.ClientMetadataClaims,
                backchannel.ClientMetadataClaims,
            ]
        )
    )
    authorization.register_endpoint(
        ClientConfigurationEndpoint(
            claims_classes=[
                rfc7591.ClientMetadataClaims,
                rfc9101.ClientMetadataClaims,
                oidc_registration.ClientMetadataClaims,
                rpinitiated.ClientMetadataClaims,
                backchannel.ClientMetadataClaims,
            ]
        )
    )

    authorization.register_extension(IssuerParameter())
    authorization.register_extension(MultipleResponseTypes([FormPost()]))
    authorization.register_extension(rfc9470.StepUpAuthentication())
    authorization.register_extension(PromptValues())
    authorization.register_extension(JWTAuthenticationRequest())
