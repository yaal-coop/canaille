import datetime
from authlib.integrations.flask_oauth2 import (
    AuthorizationServer,
    ResourceProtector,
)
from authlib.oauth2.rfc6749 import grants, util
from authlib.oauth2.rfc6750 import BearerTokenValidator
from authlib.oauth2.rfc7009 import RevocationEndpoint
from authlib.oauth2.rfc7636 import CodeChallenge
from .models import User, Client, Authorization, Token


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = [
        "client_secret_basic",
        "client_secret_post",
        "none",
    ]

    def save_authorization_code(self, code, request):
        raise NotImplementedError()
        code_challenge = request.data.get("code_challenge")
        code_challenge_method = request.data.get("code_challenge_method")
        auth_code = Authorization(
            code=code,
            client_id=request.client.client_id,
            redirect_uri=request.redirect_uri,
            scope=request.scope,
            user_id=request.user.id,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )
        #db.session.add(auth_code)
        #db.session.commit()
        return auth_code

    def query_authorization_code(self, code, client):
        raise NotImplementedError()
        auth_code = Authorization.query.filter_by(
            code=code, client_id=client.client_id
        ).first()
        if auth_code and not auth_code.is_expired():
            return auth_code

    def delete_authorization_code(self, authorization_code):
        raise NotImplementedError()
        pass
        #db.session.delete(authorization_code)
        #db.session.commit()

    def authenticate_user(self, authorization_code):
        raise NotImplementedError()
        return User.query.get(authorization_code.user_id)


class PasswordGrant(grants.ResourceOwnerPasswordCredentialsGrant):
    def authenticate_user(self, username, password):
        user = User.get(username)
        if user is not None and user.check_password(password):
            return user


class RefreshTokenGrant(grants.RefreshTokenGrant):
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
        #db.session.add(credential)
        #db.session.commit()


def query_client(client_id):
    return Client.get(client_id)


def save_token(token, request):
    client_id, client_secret = util.extract_basic_authorization(request.headers)
    t = Token(
        authzAccessToken=token['access_token'],
        authzScopeValue=token['scope'],
        authzAccessTokenIssueDate=datetime.datetime.now().strftime("%Y%m%d%H%M%SZ"),
        authzSubject=request.user.dn,
        authzClientID=client_id,
        authzRefreshTokenSecret=token['refresh_token'],
        authzAccessTokenLifetime=str(token['expires_in']),
        # ??? = token['type']
    )
    t.save()
    return t

class RevocationEndpoint(RevocationEndpoint):
    def query_token(self, token, token_type_hint, client):
        raise NotImplementedError()

    def revoke_token(self, token):
        raise NotImplementedError()

class BearerTokenValidator(BearerTokenValidator):
    def authenticate_token(self, token_string):
        return Token.get(token_string)

    def request_invalid(self, request):
        return False

    def token_revoked(self, token):
        return False

authorization = AuthorizationServer(query_client=query_client, save_token=save_token)
require_oauth = ResourceProtector()


def config_oauth(app):
    authorization.init_app(app)

    # support all grants
    authorization.register_grant(grants.ImplicitGrant)
    authorization.register_grant(grants.ClientCredentialsGrant)
    authorization.register_grant(AuthorizationCodeGrant, [CodeChallenge(required=True)])
    authorization.register_grant(PasswordGrant)
    authorization.register_grant(RefreshTokenGrant)

    authorization.register_endpoint(RevocationEndpoint)

    require_oauth.register_token_validator(BearerTokenValidator())
