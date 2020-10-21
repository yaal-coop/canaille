import datetime
from authlib.integrations.flask_oauth2 import AuthorizationServer, ResourceProtector
from authlib.oauth2.rfc6749.grants import (
    AuthorizationCodeGrant as _AuthorizationCodeGrant,
    ResourceOwnerPasswordCredentialsGrant as _ResourceOwnerPasswordCredentialsGrant,
    RefreshTokenGrant as _RefreshTokenGrant,
    ImplicitGrant,
    ClientCredentialsGrant,
)
from authlib.oauth2.rfc6750 import BearerTokenValidator as _BearerTokenValidator
from authlib.oauth2.rfc7009 import RevocationEndpoint as _RevocationEndpoint
from authlib.oauth2.rfc7636 import CodeChallenge as _CodeChallenge
from authlib.oauth2.rfc7662 import IntrospectionEndpoint as _IntrospectionEndpoint
from authlib.oidc.core.grants import (
    OpenIDCode as _OpenIDCode,
    OpenIDImplicitGrant as _OpenIDImplicitGrant,
    OpenIDHybridGrant as _OpenIDHybridGrant,
)
from authlib.oidc.core import UserInfo
from flask import current_app
from .models import Client, AuthorizationCode, Token, User


def exists_nonce(nonce, req):
    exists = AuthorizationCode.filter(oauthClientID=req.client_id, oauthNonce=nonce)
    return bool(exists)


def get_jwt_config(grant):
    with open(current_app.config["JWT"]["PRIVATE_KEY"]) as pk:
        return {
            "key": pk.read(),
            "alg": current_app.config["JWT"]["ALG"],
            "iss": authorization.metadata["issuer"],
            "exp": current_app.config["JWT"]["EXP"],
        }


def generate_user_info(user, scope):
    user = User.get(dn=user)
    fields = ["sub"]
    if "profile" in scope:
        fields += [
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
        fields += ["email", "email_verified"]
    if "address" in scope:
        fields += ["address"]
    if "phone" in scope:
        fields += ["phone_number", "phone_number_verified"]

    data = {}
    for field in fields:
        ldap_field_match = current_app.config["JWT"]["MAPPING"].get(field.upper())
        if ldap_field_match and ldap_field_match in user.attrs:
            data[field] = user.__getattr__(ldap_field_match)
            if isinstance(data[field], list):
                data[field] = data[field][0]

    return UserInfo(**data)


def save_authorization_code(code, request):
    nonce = request.data.get("nonce")
    now = datetime.datetime.now()
    code = AuthorizationCode(
        oauthCode=code,
        oauthSubject=request.user,
        oauthClient=request.client.dn,
        oauthRedirectURI=request.redirect_uri or request.client.oauthRedirectURIs[0],
        oauthScope=request.scope,
        oauthNonce=nonce,
        oauthAuthorizationDate=now.strftime("%Y%m%d%H%M%SZ"),
        oauthAuthorizationLifetime=str(84000),
        oauthCodeChallenge=request.data.get("code_challenge"),
        oauthCodeChallengeMethod=request.data.get("code_challenge_method"),
    )
    code.save()
    return code.oauthCode


class AuthorizationCodeGrant(_AuthorizationCodeGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ["client_secret_basic", "client_secret_post", "none"]

    def save_authorization_code(self, code, request):
        return save_authorization_code(code, request)

    def query_authorization_code(self, code, client):
        item = AuthorizationCode.filter(oauthCode=code, oauthClient=client.dn)
        if item and not item[0].is_expired():
            return item[0]

    def delete_authorization_code(self, authorization_code):
        authorization_code.delete()

    def authenticate_user(self, authorization_code):
        return User.get(dn=authorization_code.oauthSubject).dn


class OpenIDCode(_OpenIDCode):
    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_jwt_config(self, grant):
        return get_jwt_config(grant)

    def generate_user_info(self, user, scope):
        return generate_user_info(user, scope)


class PasswordGrant(_ResourceOwnerPasswordCredentialsGrant):
    def authenticate_user(self, username, password):
        return User.authenticate(username, password).dn


class RefreshTokenGrant(_RefreshTokenGrant):
    def authenticate_refresh_token(self, refresh_token):
        token = Token.filter(oauthRefreshToken=refresh_token)
        if token and token[0].is_refresh_token_active():
            return token[0]

    def authenticate_user(self, credential):
        return User.get(dn=credential.oauthSubject).dn

    def revoke_old_credential(self, credential):
        credential.oauthRevokationDate = datetime.datetime.now().strftime(
            "%Y%m%d%H%M%SZ"
        )
        credential.save()


class OpenIDImplicitGrant(_OpenIDImplicitGrant):
    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_jwt_config(self, grant=None):
        return get_jwt_config(grant)

    def generate_user_info(self, user, scope):
        return generate_user_info(user, scope)


class OpenIDHybridGrant(_OpenIDHybridGrant):
    def save_authorization_code(self, code, request):
        return save_authorization_code(code, request)

    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_jwt_config(self, grant=None):
        return get_jwt_config(grant)

    def generate_user_info(self, user, scope):
        return generate_user_info(user, scope)


def query_client(client_id):
    return Client.get(client_id)


def save_token(token, request):
    now = datetime.datetime.now()
    t = Token(
        oauthTokenType=token["token_type"],
        oauthAccessToken=token["access_token"],
        oauthIssueDate=now.strftime("%Y%m%d%H%M%SZ"),
        oauthTokenLifetime=str(token["expires_in"]),
        oauthScope=token["scope"],
        oauthClient=request.client.dn,
        oauthRefreshToken=token.get("refresh_token"),
        oauthSubject=request.user,
    )
    t.save()


class BearerTokenValidator(_BearerTokenValidator):
    def authenticate_token(self, token_string):
        return Token.get(token_string)

    def request_invalid(self, request):
        return False

    def token_revoked(self, token):
        return bool(token.oauthRevokationDate)


class RevocationEndpoint(_RevocationEndpoint):
    def query_token(self, token, token_type_hint, client):
        if token_type_hint == "access_token":
            return Token.filter(oauthClient=client.dn, oauthAccessToken=token)
        elif token_type_hint == "refresh_token":
            return Token.filter(oauthClient=client.dn, oauthRefreshToken=token)

        item = Token.filter(oauthClient=client.dn, oauthAccessToken=token)
        if item:
            return item[0]

        item = Token.filter(oauthClient=client.dn, oauthRefreshToken=token)
        if item:
            return item[0]

        return None

    def revoke_token(self, token):
        token.oauthRevokationDate = datetime.datetime.now().strftime("%Y%m%d%H%M%SZ")
        token.save()


class IntrospectionEndpoint(_IntrospectionEndpoint):
    def query_token(self, token, token_type_hint, client):
        if token_type_hint == "access_token":
            tok = Token.filter(oauthAccessToken=token)
        elif token_type_hint == "refresh_token":
            tok = Token.filter(oauthRefreshToken=token)
        else:
            tok = Token.filter(oauthAccessToken=token)
            if not tok:
                tok = Token.filter(oauthRefreshToken=token)
        if tok:
            tok = tok[0]
            if tok.oauthClient == client.dn:
                return tok
            # if has_introspect_permission(client):
            #    return tok

    def introspect_token(self, token):
        client_id = Client.get(token.oauthClient).oauthClientID
        return {
            "active": True,
            "client_id": client_id,
            "token_type": token.oauthTokenType,
            "username": User.get(dn=token.oauthSubject).name,
            "scope": token.get_scope(),
            "sub": token.oauthSubject,
            "aud": client_id,
            "iss": authorization.metadata["issuer"],
            "exp": token.get_expires_at(),
            "iat": token.get_issued_at(),
        }


class CodeChallenge(_CodeChallenge):
    def get_authorization_code_challenge(self, authorization_code):
        return authorization_code.oauthCodeChallenge

    def get_authorization_code_challenge_method(self, authorization_code):
        return authorization_code.oauthCodeChallengeMethod


authorization = AuthorizationServer()
require_oauth = ResourceProtector()


def config_oauth(app):
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
