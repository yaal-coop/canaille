import datetime
import uuid

from authlib.oauth2.rfc6749 import AuthorizationCodeMixin
from authlib.oauth2.rfc6749 import ClientMixin
from authlib.oauth2.rfc6749 import TokenMixin
from authlib.oauth2.rfc6749 import util

from ..ldaputils import LDAPObject


class Client(LDAPObject, ClientMixin):
    object_class = ["oauthClient"]
    base = "ou=clients,ou=oauth"
    id = "oauthClientID"

    @property
    def issue_date(self):
        return self.oauthIssueDate

    @property
    def preconsent(self):
        return self.oauthPreconsent

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


class AuthorizationCode(LDAPObject, AuthorizationCodeMixin):
    object_class = ["oauthAuthorizationCode"]
    base = "ou=authorizations,ou=oauth"
    id = "oauthCode"

    @property
    def issue_date(self):
        return self.oauthIssueDate

    def get_redirect_uri(self):
        return self.oauthRedirectURI

    def get_scope(self):
        return self.oauthScope

    def get_nonce(self):
        return self.oauthNonce

    def is_expired(self):
        return (
            self.oauthAuthorizationDate
            + datetime.timedelta(seconds=int(self.oauthAuthorizationLifetime))
            < datetime.datetime.now()
        )

    def get_auth_time(self):
        return int(
            (
                self.oauthAuthorizationDate - datetime.datetime(1970, 1, 1)
            ).total_seconds()
        )


class Token(LDAPObject, TokenMixin):
    object_class = ["oauthToken"]
    base = "ou=tokens,ou=oauth"
    id = "oauthAccessToken"

    @property
    def issue_date(self):
        return self.oauthIssueDate

    @property
    def expire_date(self):
        return self.oauthIssueDate + datetime.timedelta(
            seconds=int(self.oauthTokenLifetime)
        )

    @property
    def revoked(self):
        return bool(self.oauthRevokationDate)

    def get_client_id(self):
        return Client.get(self.oauthClient).oauthClientID

    def get_scope(self):
        return " ".join(self.oauthScope)

    def get_expires_in(self):
        return int(self.oauthTokenLifetime)

    def get_issued_at(self):
        return int(
            (self.oauthIssueDate - datetime.datetime(1970, 1, 1)).total_seconds()
        )

    def get_expires_at(self):
        issue_timestamp = (
            self.oauthIssueDate - datetime.datetime(1970, 1, 1)
        ).total_seconds()
        return int(issue_timestamp) + int(self.oauthTokenLifetime)

    def is_refresh_token_active(self):
        if self.oauthRevokationDate:
            return False

        return self.expire_date >= datetime.datetime.now()

    def is_expired(self):
        return (
            self.oauthIssueDate
            + datetime.timedelta(seconds=int(self.oauthTokenLifetime))
            < datetime.datetime.now()
        )


class Consent(LDAPObject):
    object_class = ["oauthConsent"]
    base = "ou=consents,ou=oauth"
    id = "cn"

    def __init__(self, *args, **kwargs):
        if "cn" not in kwargs:
            kwargs["cn"] = str(uuid.uuid4())

        super().__init__(*args, **kwargs)

    @property
    def issue_date(self):
        return self.oauthIssueDate

    @property
    def revokation_date(self):
        return self.oauthRevokationDate

    def revoke(self):
        self.oauthRevokationDate = datetime.datetime.now()
        self.save()

        tokens = Token.filter(
            oauthClient=self.oauthClient,
            oauthSubject=self.oauthSubject,
        )
        for t in tokens:
            if t.revoked or any(
                scope not in t.oauthScope[0] for scope in self.oauthScope
            ):
                continue

            t.oauthRevokationDate = self.oauthRevokationDate
            t.save()
