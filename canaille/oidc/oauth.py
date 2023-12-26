import datetime

from authlib.integrations.flask_oauth2 import AuthorizationServer
from authlib.integrations.flask_oauth2 import ResourceProtector
from authlib.jose import JsonWebKey
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
from authlib.oauth2.rfc7591 import (
    ClientRegistrationEndpoint as _ClientRegistrationEndpoint,
)
from authlib.oauth2.rfc7592 import (
    ClientConfigurationEndpoint as _ClientConfigurationEndpoint,
)
from authlib.oauth2.rfc7636 import CodeChallenge as _CodeChallenge
from authlib.oauth2.rfc7662 import IntrospectionEndpoint as _IntrospectionEndpoint
from authlib.oidc.core import UserInfo
from authlib.oidc.core.grants import OpenIDCode as _OpenIDCode
from authlib.oidc.core.grants import OpenIDHybridGrant as _OpenIDHybridGrant
from authlib.oidc.core.grants import OpenIDImplicitGrant as _OpenIDImplicitGrant
from authlib.oidc.core.grants.util import generate_id_token
from canaille.app import models
from flask import current_app
from flask import g
from flask import request
from flask import url_for
from werkzeug.security import gen_salt


DEFAULT_JWT_KTY = "RSA"
DEFAULT_JWT_ALG = "RS256"
DEFAULT_JWT_EXP = 3600
AUTHORIZATION_CODE_LIFETIME = 84400
DEFAULT_JWT_MAPPING = {
    "SUB": "{{ user.user_name }}",
    "NAME": "{% if user.formatted_name %}{{ user.formatted_name }}{% endif %}",
    "PHONE_NUMBER": "{% if user.phone_numbers %}{{ user.phone_numbers[0] }}{% endif %}",
    "EMAIL": "{% if user.preferred_email %}{{ user.preferred_email }}{% endif %}",
    "GIVEN_NAME": "{% if user.given_name %}{{ user.given_name }}{% endif %}",
    "FAMILY_NAME": "{% if user.family_name %}{{ user.family_name }}{% endif %}",
    "PREFERRED_USERNAME": "{% if user.display_name %}{{ user.display_name }}{% endif %}",
    "LOCALE": "{% if user.preferred_language %}{{ user.preferred_language }}{% endif %}",
    "ADDRESS": "{% if user.formatted_address %}{{ user.formatted_address }}{% endif %}",
    "PICTURE": "{% if user.photo %}{{ url_for('core.account.photo', user=user, field='photo', _external=True) }}{% endif %}",
    "WEBSITE": "{% if user.profile_url %}{{ user.profile_url }}{% endif %}",
}


def oauth_authorization_server():
    return {
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


def openid_configuration():
    return {
        **oauth_authorization_server(),
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
            "nonce",
        ],
        "subject_types_supported": ["pairwise", "public"],
        "id_token_signing_alg_values_supported": ["RS256", "ES256", "HS256"],
        "prompt_values_supported": ["none"]
        + (["create"] if current_app.config.get("ENABLE_REGISTRATION") else []),
    }


def exists_nonce(nonce, req):
    client = models.Client.get(id=req.client_id)
    exists = models.AuthorizationCode.query(client=client, nonce=nonce)
    return bool(exists)


def get_issuer():
    if current_app.config["OIDC"]["JWT"].get("ISS"):
        return current_app.config["OIDC"]["JWT"].get("ISS")

    if current_app.config.get("SERVER_NAME"):
        return current_app.config.get("SERVER_NAME")

    return request.url_root


def get_jwt_config(grant=None):
    return {
        "key": current_app.config["OIDC"]["JWT"]["PRIVATE_KEY"],
        "alg": current_app.config["OIDC"]["JWT"].get("ALG", DEFAULT_JWT_ALG),
        "iss": get_issuer(),
        "exp": current_app.config["OIDC"]["JWT"].get("EXP", DEFAULT_JWT_EXP),
    }


def get_jwks():
    kty = current_app.config["OIDC"]["JWT"].get("KTY", DEFAULT_JWT_KTY)
    alg = current_app.config["OIDC"]["JWT"].get("ALG", DEFAULT_JWT_ALG)
    jwk = JsonWebKey.import_key(
        current_app.config["OIDC"]["JWT"]["PUBLIC_KEY"], {"kty": kty}
    )
    return {
        "keys": [
            {
                "use": "sig",
                "alg": alg,
                **jwk,
            }
        ]
    }


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
        **DEFAULT_JWT_MAPPING,
        **(current_app.config["OIDC"]["JWT"].get("MAPPING") or {}),
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
    code.save()
    return code.code


class AuthorizationCodeGrant(_AuthorizationCodeGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post", "none"]

    def save_authorization_code(self, code, request):
        return save_authorization_code(code, request)

    def query_authorization_code(self, code, client):
        item = models.AuthorizationCode.query(code=code, client=client)
        if item and not item[0].is_expired():
            return item[0]

    def delete_authorization_code(self, authorization_code):
        authorization_code.delete()

    def authenticate_user(self, authorization_code):
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
        user = models.User.get_from_login(username)
        if not user:
            return None

        success, _ = user.check_password(password)
        if not success:
            return None

        return user


class RefreshTokenGrant(_RefreshTokenGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post", "none"]

    def authenticate_refresh_token(self, refresh_token):
        token = models.Token.query(refresh_token=refresh_token)
        if token and token[0].is_refresh_token_active():
            return token[0]

    def authenticate_user(self, credential):
        return credential.subject

    def revoke_old_credential(self, credential):
        credential.revokation_date = datetime.datetime.now(datetime.timezone.utc)
        credential.save()


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
    return models.Client.get(client_id=client_id)


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
    t.save()


class BearerTokenValidator(_BearerTokenValidator):
    def authenticate_token(self, token_string):
        return models.Token.get(access_token=token_string)


def query_token(token, token_type_hint):
    if token_type_hint == "access_token":
        return models.Token.get(access_token=token)
    elif token_type_hint == "refresh_token":
        return models.Token.get(refresh_token=token)

    item = models.Token.get(access_token=token)
    if item:
        return item

    item = models.Token.get(refresh_token=token)
    if item:
        return item

    return None


class RevocationEndpoint(_RevocationEndpoint):
    def query_token(self, token, token_type_hint):
        return query_token(token, token_type_hint)

    def revoke_token(self, token, request):
        token.revokation_date = datetime.datetime.now(datetime.timezone.utc)
        token.save()


class IntrospectionEndpoint(_IntrospectionEndpoint):
    def query_token(self, token, token_type_hint):
        return query_token(token, token_type_hint)

    def check_permission(self, token, client, request):
        return client in token.audience

    def introspect_token(self, token):
        audience = [aud.client_id for aud in token.audience]
        return {
            "active": True,
            "client_id": token.client.client_id,
            "token_type": token.type,
            "username": token.subject.formatted_name,
            "scope": token.get_scope(),
            "sub": token.subject.user_name,
            "aud": audience,
            "iss": get_issuer(),
            "exp": token.get_expires_at(),
            "iat": token.get_issued_at(),
        }


class ClientManagementMixin:
    def authenticate_token(self, request):
        if current_app.config.get("OIDC", {}).get(
            "DYNAMIC_CLIENT_REGISTRATION_OPEN", False
        ):
            return True

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return None

        bearer_token = auth_header.split()[1]
        if bearer_token not in (
            current_app.config.get("OIDC", {}).get("DYNAMIC_CLIENT_REGISTRATION_TOKENS")
            or []
        ):
            return None

        return True

    def get_server_metadata(self):
        result = openid_configuration()
        return result

    def resolve_public_key(self, request):
        # At the moment the only keypair accepted in software statement
        # is the one used to isues JWTs. This might change somedays.
        return current_app.config["OIDC"]["JWT"]["PUBLIC_KEY"]

    def client_convert_data(self, **kwargs):
        if "client_id_issued_at" in kwargs:
            kwargs["client_id_issued_at"] = datetime.datetime.fromtimestamp(
                kwargs["client_id_issued_at"], datetime.timezone.utc
            )

        if "client_secret_expires_at" in kwargs:
            kwargs["client_secret_expires_at"] = datetime.datetime.fromtimestamp(
                kwargs["client_secret_expires_at"], datetime.timezone.utc
            )

        if "scope" in kwargs and not isinstance(kwargs["scope"], list):
            kwargs["scope"] = kwargs["scope"].split(" ")

        return kwargs


class ClientRegistrationEndpoint(ClientManagementMixin, _ClientRegistrationEndpoint):
    software_statement_alg_values_supported = ["RS256"]

    def save_client(self, client_info, client_metadata, request):
        client = models.Client(
            # this won't be needed when OIDC RP Initiated Logout is
            # directly implemented in authlib:
            # https://gitlab.com/yaal/canaille/-/issues/157
            post_logout_redirect_uris=request.data.get("post_logout_redirect_uris"),
            **self.client_convert_data(**client_info, **client_metadata),
        )
        client.audience = [client]
        client.save()
        return client


class ClientConfigurationEndpoint(ClientManagementMixin, _ClientConfigurationEndpoint):
    def authenticate_client(self, request):
        client_id = request.uri.split("/")[-1]
        return models.Client.get(client_id=client_id)

    def revoke_access_token(self, request, token):
        pass

    def check_permission(self, client, request):
        return True

    def delete_client(self, client, request):
        client.delete()

    def update_client(self, client, client_metadata, request):
        client.update(**self.client_convert_data(**client_metadata))
        client.save()
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


authorization = AuthorizationServer()
require_oauth = ResourceProtector()


def generate_access_token(client, grant_type, user, scope):
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
    authorization.init_app(app, query_client=query_client, save_token=save_token)

    authorization.register_grant(PasswordGrant)
    authorization.register_grant(ImplicitGrant)
    authorization.register_grant(RefreshTokenGrant)
    authorization.register_grant(ClientCredentialsGrant)

    authorization.register_grant(
        AuthorizationCodeGrant,
        [
            OpenIDCode(
                require_nonce=app.config.get("OIDC", {}).get("REQUIRE_NONCE", True)
            ),
            CodeChallenge(required=True),
        ],
    )
    authorization.register_grant(OpenIDImplicitGrant)
    authorization.register_grant(OpenIDHybridGrant)

    require_oauth.register_token_validator(BearerTokenValidator())

    authorization.register_endpoint(IntrospectionEndpoint)
    authorization.register_endpoint(RevocationEndpoint)
    authorization.register_endpoint(ClientRegistrationEndpoint)
    authorization.register_endpoint(ClientConfigurationEndpoint)
