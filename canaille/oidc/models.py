import datetime
from typing import ClassVar

from authlib.oauth2.rfc6749 import AuthorizationCodeMixin
from authlib.oauth2.rfc6749 import ClientMixin
from authlib.oauth2.rfc6749 import TokenMixin
from authlib.oauth2.rfc6749 import util
from blinker import signal

from canaille.app import models
from canaille.backends import Backend

from .basemodels import AuthorizationCode as BaseAuthorizationCode
from .basemodels import Client as BaseClient
from .basemodels import Consent as BaseConsent
from .basemodels import Token as BaseToken


class Client(BaseClient, ClientMixin):
    client_info_attributes: ClassVar[list[str]] = [
        "client_id",
        "client_secret",
        "client_id_issued_at",
        "client_secret_expires_at",
    ]

    client_metadata_attributes: ClassVar[list[str]] = [
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
        "jwks",
        "token_endpoint_auth_method",
        "token_endpoint_auth_signing_alg",
        "software_id",
        "software_version",
        "sector_identifier_uri",
        "subject_type",
        "application_type",
        "id_token_signed_response_alg",
        "id_token_encrypted_response_alg",
        "id_token_encrypted_response_enc",
        "userinfo_signed_response_alg",
        "userinfo_encrypted_response_alg",
        "userinfo_encrypted_response_enc",
        "default_max_age",
        "require_auth_time",
        "default_acr_values",
        "initiate_login_uri",
        "request_object_signing_alg",
        "request_object_encryption_alg",
        "request_object_encryption_enc",
        "request_uris",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        signal("before_client_delete").connect(self.on_delete, sender=self)

    def get_client_id(self):
        return self.client_id

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
            return method == self.token_endpoint_auth_method or (
                method == "client_assertion_jwt"
                and self.token_endpoint_auth_method
                in ("client_secret_jwt", "private_key_jwt")
            )
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

    @classmethod
    def on_delete(cls, self, data):
        for consent in Backend.instance.query(models.Consent, client=self):
            Backend.instance.delete(consent)

        for code in Backend.instance.query(models.AuthorizationCode, client=self):
            Backend.instance.delete(code)

        for token in Backend.instance.query(models.Token, client=self):
            Backend.instance.delete(token)


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

    def get_auth_time(self) -> int | None:
        return self.auth_time.timestamp() if self.auth_time else None


class Token(BaseToken, TokenMixin):
    @property
    def expire_date(self):
        return self.issue_date + datetime.timedelta(seconds=int(self.lifetime))

    @property
    def revoked(self):
        return bool(self.revokation_date)

    def get_scope(self):
        return " ".join(self.scope)

    def get_issued_at(self) -> int:
        return int(self.issue_date.timestamp())

    def get_expires_at(self) -> int:
        return self.get_issued_at() + int(self.lifetime)

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
        Backend.instance.save(self)

        tokens = Backend.instance.query(
            models.Token,
            client=self.client,
            subject=self.subject,
        )
        tokens = [token for token in tokens if not token.revoked]
        for t in tokens:
            t.revokation_date = self.revokation_date
            Backend.instance.save(t)

    def restore(self):
        self.revokation_date = None
        Backend.instance.save(self)
