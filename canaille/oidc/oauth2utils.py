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
from authlib.oauth2.rfc7636 import CodeChallenge as _CodeChallenge
from authlib.oauth2.rfc7662 import IntrospectionEndpoint as _IntrospectionEndpoint
from authlib.oidc.core import UserInfo
from authlib.oidc.core.grants import OpenIDCode as _OpenIDCode
from authlib.oidc.core.grants import OpenIDHybridGrant as _OpenIDHybridGrant
from authlib.oidc.core.grants import OpenIDImplicitGrant as _OpenIDImplicitGrant
from flask import current_app
from werkzeug.security import gen_salt

from ..models import Group
from ..models import User
from .models import AuthorizationCode
from .models import Client
from .models import Token

DEFAULT_JWT_KTY = "RSA"
DEFAULT_JWT_ALG = "RS256"
DEFAULT_JWT_EXP = 3600


def exists_nonce(nonce, req):
    exists = AuthorizationCode.filter(client=req.client_id, nonce=nonce)
    return bool(exists)


def get_jwt_config(grant):

    with open(current_app.config["JWT"]["PRIVATE_KEY"]) as pk:
        return {
            "key": pk.read(),
            "alg": current_app.config["JWT"].get("ALG", DEFAULT_JWT_ALG),
            "iss": authorization.metadata["issuer"],
            "exp": current_app.config["JWT"].get("EXP", DEFAULT_JWT_EXP),
        }


def generate_user_info(user, scope):
    user = User.get(dn=user)
    claims = ["sub"]
    if "profile" in scope:
        claims += [
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
        ]
    if "email" in scope:
        claims += ["email", "email_verified"]
    if "address" in scope:
        claims += ["address"]
    if "phone" in scope:
        claims += ["phone_number", "phone_number_verified"]
    if "groups" in scope:
        claims += ["groups"]

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
            group_name_attr = current_app.config["LDAP"].get(
                "GROUP_NAME_ATTRIBUTE", Group.DEFAULT_NAME_ATTRIBUTE
            )
            data[claim] = [getattr(g, group_name_attr)[0] for g in user.groups]
    return data


def save_authorization_code(code, request):
    nonce = request.data.get("nonce")
    now = datetime.datetime.now()
    code = AuthorizationCode(
        authorization_code_id=gen_salt(48),
        code=code,
        subject=request.user,
        client=request.client.dn,
        redirect_uri=request.redirect_uri or request.client.redirect_uris[0],
        scope=request.scope,
        nonce=nonce,
        issue_date=now,
        lifetime=str(84000),
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
        lifetime=str(token["expires_in"]),
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

    def request_invalid(self, request):
        return False

    def token_revoked(self, token):
        return bool(token.revokation_date)


class RevocationEndpoint(_RevocationEndpoint):
    def query_token(self, token, token_type_hint, client):
        if token_type_hint == "access_token":
            return Token.filter(client=client.dn, access_token=token)
        elif token_type_hint == "refresh_token":
            return Token.filter(client=client.dn, refresh_token=token)

        item = Token.filter(client=client.dn, access_token=token)
        if item:
            return item[0]

        item = Token.filter(client=client.dn, refresh_token=token)
        if item:
            return item[0]

        return None

    def revoke_token(self, token):
        token.revokation_date = datetime.datetime.now()
        token.save()


class IntrospectionEndpoint(_IntrospectionEndpoint):
    def query_token(self, token, token_type_hint, client):
        if token_type_hint == "access_token":
            tok = Token.filter(access_token=token)
        elif token_type_hint == "refresh_token":
            tok = Token.filter(refresh_token=token)
        else:
            tok = Token.filter(access_token=token)
            if not tok:
                tok = Token.filter(refresh_token=token)
        if tok:
            tok = tok[0]
            if client.dn in tok.audience:
                return tok

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
            "iss": authorization.metadata["issuer"],
            "exp": token.get_expires_at(),
            "iat": token.get_issued_at(),
        }


class CodeChallenge(_CodeChallenge):
    def get_authorization_code_challenge(self, authorization_code):
        return authorization_code.challenge

    def get_authorization_code_challenge_method(self, authorization_code):
        return authorization_code.challenge_method


def generate_access_token(client, grant_type, user, scope):
    return gen_salt(48)


authorization = AuthorizationServer()
require_oauth = ResourceProtector()


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
