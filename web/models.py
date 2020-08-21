import ldap
import time
import datetime
from authlib.common.encoding import json_loads, json_dumps
from authlib.oauth2.rfc6749 import (
    ClientMixin,
    TokenMixin,
    AuthorizationCodeMixin,
    util,
)
from flask import current_app, session
from .ldaputils import LDAPObjectHelper


class User(LDAPObjectHelper):
    objectClass = ["person", "simpleSecurityObject", "uidObject"]
    base = "ou=users"
    id = "cn"
    admin = False

    @classmethod
    def get(cls, dn=None, filter=None, conn=None):
        conn = conn or cls.ldap()

        user = super().get(dn, filter, conn)
        admin_filter = current_app.config["LDAP"].get("ADMIN_FILTER")
        if (
            admin_filter
            and user
            and conn.search_s(user.dn, ldap.SCOPE_SUBTREE, admin_filter)
        ):

            user.admin = True
        return user

    @classmethod
    def authenticate(cls, login, password, signin=False):
        filter = current_app.config["LDAP"].get("USER_FILTER").format(login=login)
        user = User.get(filter=filter)
        if not user or not user.check_password(password):
            return None

        if signin:
            user.login()

        return user

    def login(self):
        session["user_dn"] = self.dn

    def logout(self):
        try:
            del session["user_dn"]
        except KeyError:
            pass

    def check_password(self, password):
        conn = ldap.initialize(current_app.config["LDAP"]["URI"])
        try:
            conn.simple_bind_s(self.dn, password)
            return True
        except ldap.INVALID_CREDENTIALS:
            return False
        finally:
            conn.unbind_s()

    @property
    def name(self):
        return self.cn[0]


class Client(LDAPObjectHelper, ClientMixin):
    objectClass = ["oauthClient"]
    base = "ou=clients"
    id = "oauthClientID"

    @property
    def issue_date(self):
        return datetime.datetime.strptime(self.oauthIssueDate, "%Y%m%d%H%M%SZ")

    def get_client_id(self):
        return self.oauthClientID

    def get_default_redirect_uri(self):
        return self.oauthRedirectURIs[0]

    def get_allowed_scope(self, scope):
        return util.list_to_scope(self.oauthScope)

    def check_redirect_uri(self, redirect_uri):
        return redirect_uri in self.oauthRedirectURIs

    def has_client_secret(self):
        return bool(self.oauthClientSecret)

    def check_client_secret(self, client_secret):
        return client_secret == self.oauthClientSecret

    def check_token_endpoint_auth_method(self, method):
        return method == self.oauthTokenEndpointAuthMethod

    def check_response_type(self, response_type):
        return all(r in self.oauthResponseType for r in response_type.split(" "))

    def check_grant_type(self, grant_type):
        return grant_type in self.oauthGrantType

    @property
    def client_info(self):
        return dict(
            client_id=self.client_id,
            client_secret=self.client_secret,
            client_id_issued_at=self.client_id_issued_at,
            client_secret_expires_at=self.client_secret_expires_at,
        )

    @property
    def client_metadata(self):
        if "client_metadata" in self.__dict__:
            return self.__dict__["client_metadata"]
        if self._client_metadata:
            data = json_loads(self._client_metadata)
            self.__dict__["client_metadata"] = data
            return data
        return {}

    def set_client_metadata(self, value):
        self._client_metadata = json_dumps(value)

    @property
    def redirect_uris(self):
        return self.client_metadata.get("redirect_uris", [])

    @property
    def token_endpoint_auth_method(self):
        return self.client_metadata.get(
            "token_endpoint_auth_method", "client_secret_basic"
        )


class AuthorizationCode(LDAPObjectHelper, AuthorizationCodeMixin):
    objectClass = ["oauthAuthorizationCode"]
    base = "ou=authorizations"
    id = "oauthCode"

    def get_redirect_uri(self):
        return self.oauthRedirectURI

    def get_scope(self):
        return self.oauthScope

    def get_nonce(self):
        return self.oauthNonce

    def is_expired(self):
        return (
            datetime.datetime.strptime(self.oauthAuthorizationDate, "%Y%m%d%H%M%SZ")
            + datetime.timedelta(seconds=int(self.oauthAuthorizationLifetime))
            < datetime.datetime.now()
        )

    def get_auth_time(self):
        auth_time = datetime.datetime.strptime(
            self.oauthAuthorizationDate, "%Y%m%d%H%M%SZ"
        )
        return (auth_time - datetime.datetime(1970, 1, 1)).total_seconds()


class Token(LDAPObjectHelper, TokenMixin):
    objectClass = ["oauthToken"]
    base = "ou=tokens"
    id = "oauthAccessToken"

    def get_client_id(self):
        return self.authzClientID

    def get_scope(self):
        return " ".join(self.oauthScope)

    def get_expires_in(self):
        return int(self.oauthTokenLifetime)

    def get_expires_at(self):
        issue_date = datetime.datetime.strptime(self.oauthIssueDate, "%Y%m%d%H%M%SZ")
        issue_timestamp = (issue_date - datetime.datetime(1970, 1, 1)).total_seconds()
        return issue_timestamp + int(self.oauthTokenLifetime)

    def is_refresh_token_active(self):
        if self.revoked:
            return False
        expires_at = self.issued_at + self.expires_in * 2
        return expires_at >= time.time()
