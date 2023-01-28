import datetime

from authlib.oauth2.rfc6749 import AuthorizationCodeMixin
from authlib.oauth2.rfc6749 import ClientMixin
from authlib.oauth2.rfc6749 import TokenMixin
from authlib.oauth2.rfc6749 import util
from canaille.ldap_backend.ldapobject import LDAPObject


class Client(LDAPObject, ClientMixin):
    object_class = ["oauthClient"]
    base = "ou=clients,ou=oauth"
    rdn = "oauthClientID"

    client_info_attributes = {
        "client_id": "oauthClientID",
        "client_secret": "oauthClientSecret",
        "client_id_issued_at": "oauthIssueDate",
        "client_secret_expires_at": "oauthClientSecretExpDate",
    }

    client_metadata_attributes = {
        "client_name": "oauthClientName",
        "contacts": "oauthClientContact",
        "client_uri": "oauthClientURI",
        "redirect_uris": "oauthRedirectURIs",
        "logo_uri": "oauthLogoURI",
        "grant_types": "oauthGrantType",
        "response_types": "oauthResponseType",
        "scope": "oauthScope",
        "tos_uri": "oauthTermsOfServiceURI",
        "policy_uri": "oauthPolicyURI",
        "jwks_uri": "oauthJWKURI",
        "jwk": "oauthJWK",
        "token_endpoint_auth_method": "oauthTokenEndpointAuthMethod",
        "software_id": "oauthSoftwareID",
        "software_version": "oauthSoftwareVersion",
    }

    attribute_table = {
        "description": "description",
        "preconsent": "oauthPreconsent",
        # post_logout_redirect_uris is not yet supported by authlib
        "post_logout_redirect_uris": "oauthPostLogoutRedirectURI",
        "audience": "oauthAudience",
        **client_info_attributes,
        **client_metadata_attributes,
    }

    def get_client_id(self):
        return self.client_id

    def get_default_redirect_uri(self):
        return self.redirect_uris[0]

    def get_allowed_scope(self, scope):
        return util.list_to_scope(
            [scope_piece for scope_piece in self.scope if scope_piece in scope]
        )

    def check_redirect_uri(self, redirect_uri):
        return redirect_uri in self.redirect_uris

    def check_client_secret(self, client_secret):
        return client_secret == self.client_secret

    def check_endpoint_auth_method(self, method, endpoint):
        if endpoint == "token":
            return method == self.token_endpoint_auth_method
        return True

    def check_response_type(self, response_type):
        return all(r in self.response_types for r in response_type.split(" "))

    def check_grant_type(self, grant_type):
        return grant_type in self.grant_types

    @property
    def client_info(self):
        result = {
            attribute_name: getattr(self, attribute_name)
            for attribute_name in self.client_info_attributes
        }
        result["client_id_issued_at"] = int(
            datetime.datetime.timestamp(result["client_id_issued_at"])
        )
        return result

    @property
    def client_metadata(self):
        metadata = {
            attribute_name: getattr(self, attribute_name)
            for attribute_name in self.client_metadata_attributes
        }
        if "scope" in metadata:
            metadata["scope"] = " ".join(metadata["scope"])
        return metadata


class AuthorizationCode(LDAPObject, AuthorizationCodeMixin):
    object_class = ["oauthAuthorizationCode"]
    base = "ou=authorizations,ou=oauth"
    rdn = "oauthAuthorizationCodeID"
    attribute_table = {
        "authorization_code_id": "oauthAuthorizationCodeID",
        "description": "description",
        "code": "oauthCode",
        "client": "oauthClient",
        "subject": "oauthSubject",
        "redirect_uri": "oauthRedirectURI",
        "response_type": "oauthResponseType",
        "scope": "oauthScope",
        "nonce": "oauthNonce",
        "issue_date": "oauthAuthorizationDate",
        "lifetime": "oauthAuthorizationLifetime",
        "challenge": "oauthCodeChallenge",
        "challenge_method": "oauthCodeChallengeMethod",
        "revokation_date": "oauthRevokationDate",
    }

    def get_redirect_uri(self):
        return self.redirect_uri

    def get_scope(self):
        return self.scope[0].split(" ")

    def get_nonce(self):
        return self.nonce

    def is_expired(self):
        return (
            self.issue_date + datetime.timedelta(seconds=int(self.lifetime))
            < datetime.datetime.now()
        )

    def get_auth_time(self):
        return int((self.issue_date - datetime.datetime(1970, 1, 1)).total_seconds())


class Token(LDAPObject, TokenMixin):
    object_class = ["oauthToken"]
    base = "ou=tokens,ou=oauth"
    rdn = "oauthTokenID"
    attribute_table = {
        "token_id": "oauthTokenID",
        "access_token": "oauthAccessToken",
        "description": "description",
        "client": "oauthClient",
        "subject": "oauthSubject",
        "type": "oauthTokenType",
        "refresh_token": "oauthRefreshToken",
        "scope": "oauthScope",
        "issue_date": "oauthIssueDate",
        "lifetime": "oauthTokenLifetime",
        "revokation_date": "oauthRevokationDate",
        "audience": "oauthAudience",
    }

    @property
    def expire_date(self):
        return self.issue_date + datetime.timedelta(seconds=int(self.lifetime))

    @property
    def revoked(self):
        return bool(self.revokation_date)

    def get_scope(self):
        return " ".join(self.scope)

    def get_expires_in(self):
        return int(self.lifetime)

    def get_issued_at(self):
        return int((self.issue_date - datetime.datetime(1970, 1, 1)).total_seconds())

    def get_expires_at(self):
        issue_timestamp = (
            self.issue_date - datetime.datetime(1970, 1, 1)
        ).total_seconds()
        return int(issue_timestamp) + int(self.lifetime)

    def is_refresh_token_active(self):
        if self.revokation_date:
            return False

        return self.expire_date >= datetime.datetime.now()

    def is_expired(self):
        return (
            self.issue_date + datetime.timedelta(seconds=int(self.lifetime))
            < datetime.datetime.now()
        )

    def is_revoked(self):
        return bool(self.revokation_date)

    def check_client(self, client):
        return client.client_id == Client.get(self.client).client_id


class Consent(LDAPObject):
    object_class = ["oauthConsent"]
    base = "ou=consents,ou=oauth"
    rdn = "cn"
    attribute_table = {
        "cn": "cn",
        "subject": "oauthSubject",
        "client": "oauthClient",
        "scope": "oauthScope",
        "issue_date": "oauthIssueDate",
        "revokation_date": "oauthRevokationDate",
    }

    def revoke(self):
        self.revokation_date = datetime.datetime.now()
        self.save()

        tokens = Token.filter(
            oauthClient=self.client,
            oauthSubject=self.subject,
        )
        for t in tokens:
            different_scope = any(scope not in t.scope[0] for scope in self.scope)
            if t.revoked or different_scope:
                continue

            t.revokation_date = self.revokation_date
            t.save()
