import datetime
from typing import ClassVar

from authlib.oauth2.rfc6749 import ClientMixin
from authlib.oauth2.rfc6749 import TokenMixin
from authlib.oauth2.rfc6749 import util
from authlib.oauth2.rfc8628 import DeviceCredentialMixin
from authlib.oidc.core import AuthorizationCodeMixin
from blinker import signal
from flask import current_app

from canaille.app import models
from canaille.backends import Backend
from canaille.core.configuration import Permission
from canaille.core.models import Group

from .basemodels import AuthorizationCode as BaseAuthorizationCode
from .basemodels import Client as BaseClient
from .basemodels import Consent as BaseConsent
from .basemodels import DeviceCode as BaseDeviceCode
from .basemodels import Token as BaseToken

OWNED_CLIENT_FORBIDDEN_GRANT_TYPES = {
    "client_credentials",
    "urn:ietf:params:oauth:grant-type:jwt-bearer",
}
"""The grants that owned clients cannot use, as they issue tokens without a user consent."""


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
        "require_signed_request_object",
        "post_logout_redirect_uris",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        signal("before_client_delete").connect(self.on_delete, sender=self)

    def get_client_id(self):
        return self.client_id

    def get_allowed_scope(self, scope: str | None) -> str:
        """Return the allowed scope for a token request.

        Per RFC 6749 Section 3.3, if the client omits the scope parameter,
        the server should use a pre-defined default (client's scope).
        If client has no maximum scope defined, any requested scope is allowed.
        """
        if not scope:
            return util.list_to_scope(self.scope) if self.scope else ""

        if not self.scope:
            return scope

        allowed = set(self.scope)
        requested = scope.split()
        return util.list_to_scope([s for s in requested if s in allowed])

    def check_redirect_uri(self, redirect_uri: str) -> bool:
        return redirect_uri in self.redirect_uris

    def check_client_secret(self, client_secret: str) -> bool:
        if self.secret_expired:
            current_app.logger.security(
                f"Client {self.client_id} authentication attempt with a secret "
                f"expired since {self.client_secret_expires_at}"
            )
            return False

        return client_secret == self.client_secret

    def check_endpoint_auth_method(self, method, endpoint):
        if endpoint in ("token", "device_authorization"):
            # hotfix for https://github.com/lepture/authlib/issues/759
            implicit_flow_shortcut = method == "none" and self.grant_types == [
                "implicit"
            ]
            return (
                implicit_flow_shortcut
                or method == self.token_endpoint_auth_method
                or (
                    method == "client_assertion_jwt"
                    and self.token_endpoint_auth_method
                    in ("client_secret_jwt", "private_key_jwt")
                )
            )
        return True

    def check_response_type(self, response_type):
        return all(r in self.response_types for r in response_type.split(" "))

    def check_grant_type(self, grant_type):
        if self.owners and grant_type in OWNED_CLIENT_FORBIDDEN_GRANT_TYPES:
            return False

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

        if scope := metadata.get("scope"):
            metadata["scope"] = " ".join(scope)

        return metadata

    @property
    def full_audience(self):
        """The client and the other clients of its audience."""
        return list(dict.fromkeys([self, *(self.audience or [])]))

    @classmethod
    def on_delete(cls, self, data):
        for consent in Backend.instance.query(models.Consent, client=self):
            Backend.instance.delete(consent)

        for code in Backend.instance.query(models.AuthorizationCode, client=self):
            Backend.instance.delete(code)

        for token in Backend.instance.query(models.Token, client=self):
            Backend.instance.delete(token)

        for device_code in Backend.instance.query(models.DeviceCode, client=self):
            Backend.instance.delete(device_code)

    def get_default_redirect_uri(self):
        return None

    def is_editable_by(self, user) -> bool:
        """Check if a user can edit this client."""
        if user.can(Permission.MANAGE_OIDC):
            return True

        if not user.can(Permission.MANAGE_OWN_CLIENTS):
            return False

        return self._user_can_edit(user)

    def is_usable_by(self, user) -> bool:
        """Check if a user can authenticate with this client."""
        if not user.can(Permission.USE_OIDC):
            return False

        if not self.owners:
            return True

        return self._user_can_use(user)

    def _user_can_edit(self, user) -> bool:
        """Check if a user can edit this client.

        A user can edit if they are a direct owner, or if they own a group that owns this client.
        """
        for owner in self.owners:
            if owner == user:
                return True
            if isinstance(owner, Group) and owns_group(user, owner):
                return True
        return False

    def _user_can_use(self, user) -> bool:
        """Check if a user can use this client for authentication.

        A user can use if they are a direct owner, or if they are a member of a group that owns this client.
        """
        for owner in self.owners:
            if owner == user:
                return True
            if isinstance(owner, Group) and owner in user.groups:
                return True
        return False


def owns_group(user, group) -> bool:
    """Tell whether ``user`` manages ``group`` as its owner."""
    return user in group.owners and user.can(Permission.MANAGE_OWN_GROUPS)


def owned_groups(user):
    """Return the groups that ``user`` manages as their owner."""
    if not user.can(Permission.MANAGE_OWN_GROUPS):
        return []

    return Backend.instance.query(models.Group, owners=user)


def managed_owners(user):
    """Return the owners whose clients ``user`` can edit: the user, and the groups they own."""
    return [user, *owned_groups(user)]


def delete_owned_clients(owner, data):
    """Remove a deleted user or group from the client owners.

    The clients left without owners are deleted.
    """
    if not current_app.features.has_oidc:
        return

    for client in Backend.instance.query(models.Client, owners=owner):
        owners = [other for other in client.owners if other != owner]
        if not owners:
            Backend.instance.delete(client)
            continue

        Backend.instance.update(client, owners=owners)
        Backend.instance.save(client)


def delete_user_grants(user, data):
    """Delete the consents, codes and tokens of a deleted user."""
    if not current_app.features.has_oidc:
        return

    for model in (
        models.Consent,
        models.AuthorizationCode,
        models.DeviceCode,
        models.Token,
    ):
        for instance in Backend.instance.query(model, subject=user):
            Backend.instance.delete(instance)


def setup_oidc_signals():
    teardown_oidc_signals()
    signal("before_user_delete").connect(delete_owned_clients)
    signal("before_group_delete").connect(delete_owned_clients)
    signal("after_user_delete").connect(delete_user_grants)


def teardown_oidc_signals():
    signal("before_user_delete").disconnect(delete_owned_clients)
    signal("before_group_delete").disconnect(delete_owned_clients)
    signal("after_user_delete").disconnect(delete_user_grants)


class AuthorizationCode(BaseAuthorizationCode, AuthorizationCodeMixin):
    def get_redirect_uri(self):
        return self.redirect_uri

    def get_scope(self) -> str:
        return util.list_to_scope(self.scope)

    def get_nonce(self):
        return self.nonce

    def is_expired(self):
        return self.issue_date + datetime.timedelta(
            seconds=int(self.lifetime or 0)
        ) < datetime.datetime.now(datetime.UTC)

    def get_auth_time(self) -> float | None:
        return self.auth_time.timestamp() if self.auth_time else None

    def get_acr(self):
        return self.acr

    def get_amr(self):
        return self.amr


class Token(BaseToken, TokenMixin):
    @property
    def expire_date(self):
        return self.issue_date + datetime.timedelta(seconds=self.lifetime or 0)

    @property
    def revoked(self):
        return bool(self.revokation_date)

    @property
    def full_audience(self):
        """The client that issued the token and the other clients of its audience."""
        return list(dict.fromkeys([self.client, *(self.audience or [])]))

    def get_scope(self):
        return " ".join(self.scope)

    def get_issued_at(self) -> float:
        return self.issue_date.timestamp()

    def get_expires_at(self) -> float:
        return self.get_issued_at() + (self.lifetime or 0)

    def is_refresh_token_active(self):
        if self.revokation_date:
            return False

        return self.expire_date >= datetime.datetime.now(datetime.UTC)

    def is_expired(self):
        return self.issue_date + datetime.timedelta(
            seconds=int(self.lifetime or 0)
        ) < datetime.datetime.now(datetime.UTC)

    def is_revoked(self):
        """Tell whether the token cannot be used anymore.

        This is the case after a revocation, and when its user cannot use its client anymore.
        Tokens without a user are refused for clients with owners.
        """
        if self.revokation_date:
            return True

        if not self.subject:
            return bool(self.client.owners)

        return not self.client.is_usable_by(self.subject)

    def check_client(self, client):
        return client.client_id == self.client.client_id

    def get_user(self):
        return self.subject

    def get_client(self):
        return self.client


class DeviceCode(BaseDeviceCode, DeviceCredentialMixin):
    def get_client_id(self):
        return self.client.client_id

    def get_scope(self) -> str:
        return util.list_to_scope(self.scope)

    def is_expired(self):
        return self.issue_date + datetime.timedelta(
            seconds=int(self.lifetime or 0)
        ) < datetime.datetime.now(datetime.UTC)


class Consent(BaseConsent):
    @property
    def revoked(self):
        return bool(self.revokation_date)

    def revoke(self):
        self.revokation_date = datetime.datetime.now(datetime.UTC)
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

        for device_code in Backend.instance.query(
            models.DeviceCode,
            client=self.client,
            subject=self.subject,
        ):
            Backend.instance.delete(device_code)

    def restore(self):
        self.revokation_date = None
        Backend.instance.save(self)
