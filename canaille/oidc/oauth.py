import datetime

from authlib.integrations.flask_oauth2 import AuthorizationServer
from authlib.integrations.flask_oauth2 import ResourceProtector
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
from flask import current_app
from flask import request
from werkzeug.security import gen_salt

from ..models import Group
from ..models import User
from .models import AuthorizationCode
from .models import Client
from .models import Token

DEFAULT_JWT_KTY = "RSA"
DEFAULT_JWT_ALG = "RS256"
DEFAULT_JWT_EXP = 3600
AUTHORIZATION_CODE_LIFETIME = 84400


def exists_nonce(nonce, req):
    exists = AuthorizationCode.filter(client=req.client_id, nonce=nonce)
    return bool(exists)


def get_issuer():
    if current_app.config["JWT"].get("ISS"):
        return current_app.config["JWT"].get("ISS")

    if current_app.config.get("SERVER_NAME"):
        return current_app.config.get("SERVER_NAME")

    return request.url_root


def get_jwt_config(grant):

    with open(current_app.config["JWT"]["PRIVATE_KEY"]) as pk:
        return {
            "key": pk.read(),
            "alg": current_app.config["JWT"].get("ALG", DEFAULT_JWT_ALG),
            "iss": get_issuer(),
            "exp": current_app.config["JWT"].get("EXP", DEFAULT_JWT_EXP),
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
    user = User.get(dn=user)
    claims = claims_from_scope(scope)
    data = generate_user_claims(user, claims)
    return UserInfo(**data)


def generate_user_claims(user, claims, jwt_mapping_config=None):
    jwt_mapping_config = jwt_mapping_config or current_app.config["JWT"]["MAPPING"]

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
            data[claim] = [group.name for group in user.groups]
    return data


def save_authorization_code(code, request):
    nonce = request.data.get("nonce")
    now = datetime.datetime.now()
    scope = request.client.get_allowed_scope(request.scope)
    code = AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code=code,
        subject=request.user,
        client=request.client.dn,
        redirect_uri=request.redirect_uri or request.client.redirect_uris[0],
        scope=scope,
        nonce=nonce,
        issue_date=now,
        lifetime=str(AUTHORIZATION_CODE_LIFETIME),
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
        item = AuthorizationCode.filter(code=code, client=client.dn)
        if item and not item[0].is_expired():
            return item[0]

    def delete_authorization_code(self, authorization_code):
        authorization_code.delete()

    def authenticate_user(self, authorization_code):
        user = User.get(dn=authorization_code.subject)
        if user:
            return user.dn


class OpenIDCode(_OpenIDCode):
    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_jwt_config(self, grant):
        return get_jwt_config(grant)

    def generate_user_info(self, user, scope):
        return generate_user_info(user, scope)

    def get_audiences(self, request):
        client = request.client
        return [Client.get(aud).client_id for aud in client.audience]


class PasswordGrant(_ResourceOwnerPasswordCredentialsGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post", "none"]

    def authenticate_user(self, username, password):
        user = User.authenticate(username, password)
        if user:
            return user.dn


class RefreshTokenGrant(_RefreshTokenGrant):
    def authenticate_refresh_token(self, refresh_token):
        token = Token.filter(refresh_token=refresh_token)
        if token and token[0].is_refresh_token_active():
            return token[0]

    def authenticate_user(self, credential):
        user = User.get(dn=credential.subject)
        if user:
            return user.dn

    def revoke_old_credential(self, credential):
        credential.revokation_date = datetime.datetime.now()
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
        return [Client.get(aud).client_id for aud in client.audience]


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
        return [Client.get(aud).client_id for aud in client.audience]


def query_client(client_id):
    return Client.get(client_id)


def save_token(token, request):
    now = datetime.datetime.now()
    t = Token(
        token_id=gen_salt(48),
        type=token["token_type"],
        access_token=token["access_token"],
        issue_date=now,
        lifetime=token["expires_in"],
        scope=token["scope"],
        client=request.client.dn,
        refresh_token=token.get("refresh_token"),
        subject=request.user,
        audience=request.client.audience,
    )
    t.save()


class BearerTokenValidator(_BearerTokenValidator):
    def authenticate_token(self, token_string):
        return Token.get(access_token=token_string)


def query_token(token, token_type_hint):
    if token_type_hint == "access_token":
        return Token.get(access_token=token)
    elif token_type_hint == "refresh_token":
        return Token.get(refresh_token=token)

    item = Token.get(access_token=token)
    if item:
        return item

    item = Token.get(refresh_token=token)
    if item:
        return item

    return None


class RevocationEndpoint(_RevocationEndpoint):
    def query_token(self, token, token_type_hint):
        return query_token(token, token_type_hint)

    def revoke_token(self, token, request):
        token.revokation_date = datetime.datetime.now()
        token.save()


class IntrospectionEndpoint(_IntrospectionEndpoint):
    def query_token(self, token, token_type_hint):
        return query_token(token, token_type_hint)

    def check_permission(self, token, client, request):
        return client.dn in token.audience

    def introspect_token(self, token):
        client_id = Client.get(token.client).client_id
        user = User.get(dn=token.subject)
        audience = [Client.get(aud).client_id for aud in token.audience]
        return {
            "active": True,
            "client_id": client_id,
            "token_type": token.type,
            "username": user.name,
            "scope": token.get_scope(),
            "sub": user.uid[0],
            "aud": audience,
            "iss": get_issuer(),
            "exp": token.get_expires_at(),
            "iat": token.get_issued_at(),
        }


class ClientManagementMixin:
    def authenticate_token(self, request):
        if current_app.config.get("OIDC_DYNAMIC_CLIENT_REGISTRATION_OPEN", False):
            return True

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return None

        bearer_token = auth_header.split()[1]
        if bearer_token not in current_app.config.get(
            "OIDC_DYNAMIC_CLIENT_REGISTRATION_TOKENS", []
        ):
            return None

        return True

    def get_server_metadata(self):
        from .well_known import openid_configuration

        result = openid_configuration()
        return result

    def resolve_public_key(self, request):
        # At the moment the only keypair accepted in software statement
        # is the one used to isues JWTs. This might change somedays.
        with open(current_app.config["JWT"]["PUBLIC_KEY"], "rb") as fd:
            return fd.read()


class ClientRegistrationEndpoint(ClientManagementMixin, _ClientRegistrationEndpoint):
    software_statement_alg_values_supported = ["RS256"]

    def save_client(self, client_info, client_metadata, request):
        client_info["client_id_issued_at"] = datetime.datetime.fromtimestamp(
            client_info["client_id_issued_at"]
        )
        if "scope" in client_metadata and not isinstance(
            client_metadata["scope"], list
        ):
            client_metadata["scope"] = client_metadata["scope"].split(" ")
        client = Client(**client_info, **client_metadata)
        client.save()
        return client


class ClientConfigurationEndpoint(ClientManagementMixin, _ClientConfigurationEndpoint):
    def authenticate_client(self, request):
        client_id = request.uri.split("/")[-1]
        return Client.get(client_id)

    def revoke_access_token(self, request, token):
        pass

    def check_permission(self, client, request):
        return True

    def delete_client(self, client, request):
        client.delete()

    def update_client(self, client, client_metadata, request):
        if "scope" in client_metadata and not isinstance(
            client_metadata["scope"], list
        ):
            client_metadata["scope"] = client_metadata["scope"].split(" ")
        for key, value in client_metadata.items():
            setattr(client, key, value)
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
    audience = [Client.get(dn).client_id for dn in client.audience]
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
        [OpenIDCode(require_nonce=True), CodeChallenge(required=True)],
    )
    authorization.register_grant(OpenIDImplicitGrant)
    authorization.register_grant(OpenIDHybridGrant)

    require_oauth.register_token_validator(BearerTokenValidator())

    authorization.register_endpoint(IntrospectionEndpoint)
    authorization.register_endpoint(RevocationEndpoint)
    authorization.register_endpoint(ClientRegistrationEndpoint)
    authorization.register_endpoint(ClientConfigurationEndpoint)
