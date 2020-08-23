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
from authlib.oidc.core.grants import (
    OpenIDCode as _OpenIDCode,
    OpenIDImplicitGrant as _OpenIDImplicitGrant,
    OpenIDHybridGrant as _OpenIDHybridGrant,
)
from authlib.oidc.core import UserInfo
from werkzeug.security import gen_salt
from .models import Client, AuthorizationCode, Token, User

DUMMY_JWT_CONFIG = {
    "key": "secret-key",
    "alg": "HS256",
    "iss": "https://authlib.org",
    "exp": 3600,
}


def exists_nonce(nonce, req):
    exists = AuthorizationCode.filter(oauthClientID=req.client_id, oauthNonce=nonce)
    return bool(exists)


def generate_user_info(user, scope):
    return UserInfo(
        sub=user.uid[0],
        name=user.sn[0],
        email="toto@yolo.com",
        phone_number=user.telephoneNumber,
#        given_name
#        family_name,
#        middle_name,
#        nickname,
#        preferred_username,
#        profile,
#        picture,
#        website,
#        email,
#        email_verified,
#        gender,
#        birthdate,
#        zoneinfo,
#        locale,
#        phone_number_verified,
#        address,
#        updated_at,
    )


def save_authorization_code(code, request):
    nonce = request.data.get("nonce")
    now = datetime.datetime.now()
    code = AuthorizationCode(
        oauthCode=code,
        oauthSubject=request.user,
        oauthClientID=request.client.oauthClientID,
        oauthRedirectURI=request.redirect_uri or request.client.oauthRedirectURIs[0],
        oauthScope=request.scope,
        oauthNonce=nonce,
        oauthAuthorizationDate=now.strftime("%Y%m%d%H%M%SZ"),
        oauthAuthorizationLifetime=str(84000),
    )
    code.save()
    return code.oauthCode


class AuthorizationCodeGrant(_AuthorizationCodeGrant):
    def save_authorization_code(self, code, request):
        return save_authorization_code(code, request)

    def query_authorization_code(self, code, client):
        item = AuthorizationCode.filter(
            oauthCode=code, oauthClientID=client.oauthClientID
        )
        if item and not item[0].is_expired():
            return item[0]

    def delete_authorization_code(self, authorization_code):
        authorization_code.delete()

    def authenticate_user(self, authorization_code):
        return User.get(authorization_code.oauthSubject)


class OpenIDCode(_OpenIDCode):
    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_jwt_config(self, grant):
        return DUMMY_JWT_CONFIG

    def generate_user_info(self, user, scope):
        return generate_user_info(user, scope)


class PasswordGrant(_ResourceOwnerPasswordCredentialsGrant):
    def authenticate_user(self, username, password):
        return User.authenticate(username, password)


class RefreshTokenGrant(_RefreshTokenGrant):
    def authenticate_refresh_token(self, refresh_token):
        raise NotImplementedError()
        token = Token.query.filter_by(refresh_token=refresh_token).first()
        if token and token.is_refresh_token_active():
            return token

    def authenticate_user(self, credential):
        raise NotImplementedError()
        return User.query.get(credential.user_id)

    def revoke_old_credential(self, credential):
        raise NotImplementedError()
        credential.revoked = True


class OpenIDImplicitGrant(_OpenIDImplicitGrant):
    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_jwt_config(self, grant=None):
        return DUMMY_JWT_CONFIG

    def generate_user_info(self, user, scope):
        user = User.get(user)
        return generate_user_info(user, scope)


class OpenIDHybridGrant(_OpenIDHybridGrant):
    def create_authorization_code(self, client, grant_user, request):
        code = gen_salt(48)
        return self.save_authorization_code(code, request)

    def save_authorization_code(self, code, request):
        return save_authorization_code(code, request)

    def exists_nonce(self, nonce, request):
        return exists_nonce(nonce, request)

    def get_jwt_config(self):
        return DUMMY_JWT_CONFIG

    def generate_user_info(self, user, scope):
        user = User.get(user)
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
        oauthClientID=request.client.oauthClientID,
    )
    if "refresh_token" in token:
        t.oauthRefreshToken = token["refresh_token"]
    t.save()


class BearerTokenValidator(_BearerTokenValidator):
    def authenticate_token(self, token_string):
        return Token.get(token_string)

    def request_invalid(self, request):
        return False

    def token_revoked(self, token):
        return False


authorization = AuthorizationServer()
require_oauth = ResourceProtector()


def config_oauth(app):
    authorization.init_app(app, query_client=query_client, save_token=save_token)

    authorization.register_grant(PasswordGrant)
    authorization.register_grant(ImplicitGrant)
    authorization.register_grant(ClientCredentialsGrant)

    authorization.register_grant(
        AuthorizationCodeGrant, [OpenIDCode(require_nonce=True)]
    )
    authorization.register_grant(OpenIDImplicitGrant)
    authorization.register_grant(OpenIDHybridGrant)

    require_oauth.register_token_validator(BearerTokenValidator())
