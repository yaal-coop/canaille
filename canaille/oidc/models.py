import datetime

from authlib.oauth2.rfc6749 import AuthorizationCodeMixin
from authlib.oauth2.rfc6749 import ClientMixin
from authlib.oauth2.rfc6749 import TokenMixin
from authlib.oauth2.rfc6749 import util
from canaille.app import models

from .basemodels import AuthorizationCode as BaseAuthorizationCode
from .basemodels import Client as BaseClient
from .basemodels import Consent as BaseConsent
from .basemodels import Token as BaseToken


class Client(BaseClient, ClientMixin):
    client_info_attributes = [
        "client_id",
        "client_secret",
        "client_id_issued_at",
        "client_secret_expires_at",
    ]

    client_metadata_attributes = [
        "client_name",
        "contacts",
        "client_uri",
        "redirect_uris",
        "logo_uri",
        "grant_types",
        "response_types",
        "scope",
        "tos_uri",
        "policy_uri",
        "jwks_uri",
        "jwk",
        "token_endpoint_auth_method",
        "software_id",
        "software_version",
    ]

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
        result["client_secret_expires_at"] = (
            int(datetime.datetime.timestamp(result["client_secret_expires_at"]))
            if result["client_secret_expires_at"]
            else 0
        )
        return result

    @property
    def client_metadata(self):
        metadata = {
            attribute_name: getattr(self, attribute_name)
            for attribute_name in self.client_metadata_attributes
        }
        metadata["scope"] = " ".join(metadata["scope"])
        return metadata

    def delete(self):
        for consent in models.Consent.query(client=self):
            consent.delete()

        for code in models.AuthorizationCode.query(client=self):
            code.delete()

        for token in models.Token.query(client=self):
            token.delete()

        super().delete()


class AuthorizationCode(BaseAuthorizationCode, AuthorizationCodeMixin):
    def get_redirect_uri(self):
        return self.redirect_uri

    def get_scope(self):
        return self.scope

    def get_nonce(self):
        return self.nonce

    def is_expired(self):
        return self.issue_date + datetime.timedelta(
            seconds=int(self.lifetime)
        ) < datetime.datetime.now(datetime.timezone.utc)

    def get_auth_time(self):
        return int(
            (
                self.issue_date
                - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
            ).total_seconds()
        )


class Token(BaseToken, TokenMixin):
    @property
    def expire_date(self):
        return self.issue_date + datetime.timedelta(seconds=int(self.lifetime))

    @property
    def revoked(self):
        return bool(self.revokation_date)

    def get_scope(self):
        return " ".join(self.scope)

    def get_issued_at(self):
        return int(
            (
                self.issue_date
                - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
            ).total_seconds()
        )

    def get_expires_at(self):
        issue_timestamp = (
            self.issue_date
            - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
        ).total_seconds()
        return int(issue_timestamp) + int(self.lifetime)

    def is_refresh_token_active(self):
        if self.revokation_date:
            return False

        return self.expire_date >= datetime.datetime.now(datetime.timezone.utc)

    def is_expired(self):
        return self.issue_date + datetime.timedelta(
            seconds=int(self.lifetime)
        ) < datetime.datetime.now(datetime.timezone.utc)

    def is_revoked(self):
        return bool(self.revokation_date)

    def check_client(self, client):
        return client.client_id == self.client.client_id


class Consent(BaseConsent):
    @property
    def revoked(self):
        return bool(self.revokation_date)

    def revoke(self):
        self.revokation_date = datetime.datetime.now(datetime.timezone.utc)
        self.save()

        tokens = models.Token.query(
            client=self.client,
            subject=self.subject,
        )
        tokens = [token for token in tokens if not token.revoked]
        for t in tokens:
            t.revokation_date = self.revokation_date
            t.save()

    def restore(self):
        self.revokation_date = None
        self.save()
