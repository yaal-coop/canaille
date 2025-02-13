from typing import ClassVar

import ldap.filter
from blinker import signal

import canaille.core.models
import canaille.oidc.models

from .backend import LDAPBackend
from .ldapobject import LDAPObject


class User(canaille.core.models.User, LDAPObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        signal("before_user_save").connect(self.before_save, sender=self)
        signal("after_user_save").connect(self.after_save, sender=self)

    attribute_map: ClassVar[dict[str, str] | None] = {
        "id": "entryUUID",
        "created": "createTimestamp",
        "last_modified": "modifyTimestamp",
        "user_name": "uid",
        "password": "userPassword",
        "preferred_language": "preferredLanguage",
        "family_name": "sn",
        "given_name": "givenName",
        "formatted_name": "cn",
        "display_name": "displayName",
        "emails": "mail",
        "phone_numbers": "telephoneNumber",
        "formatted_address": "postalAddress",
        "street": "street",
        "postal_code": "postalCode",
        "locality": "l",
        "region": "st",
        "photo": "jpegPhoto",
        "profile_url": "labeledURI",
        "employee_number": "employeeNumber",
        "department": "departmentNumber",
        "title": "title",
        "organization": "o",
        "groups": "memberOf",
        "lock_date": "pwdEndTime",
        "secret_token": "oathSecret",
        "last_otp_login": "oathLastLogin",
        "hotp_counter": "oathHOTPCounter",
        "one_time_password": "oathTokenPIN",
        "one_time_password_emission_date": "oathSecretTime",
        "password_failure_timestamps": "pwdFailureTime",
        "password_last_update": "pwdChangedTime",
    }

    def match_filter(self, filter):
        if isinstance(filter, str):
            conn = LDAPBackend.instance.connection
            return self.dn and conn.search_s(self.dn, ldap.SCOPE_SUBTREE, filter)

        return super().match_filter(filter)

    @classmethod
    def before_save(cls, self, data):
        data["group_attr"] = self.python_attribute_to_ldap("groups")
        if data["group_attr"] not in self.changes:
            return

        # The LDAP attribute memberOf cannot directly be edited,
        # so this is needed to update the Group.member attribute
        # instead.
        data["old_groups"] = (
            self.get_ldap_attribute(data["group_attr"], lookup_changes=False) or []
        )
        data["new_groups"] = (
            self.get_ldap_attribute(data["group_attr"], lookup_state=False) or []
        )
        data["to_add"] = set(data["new_groups"]) - set(data["old_groups"])
        data["to_del"] = set(data["old_groups"]) - set(data["new_groups"])
        del self.changes[data["group_attr"]]

    @classmethod
    def after_save(cls, self, data):
        for group in data.get("to_add", []):
            group.members = group.members + [self]
            LDAPBackend.instance.save(group)

        for group in data.get("to_del", []):
            # LDAP groups cannot be empty because groupOfNames.member
            # is a MUST attribute.
            # https://www.rfc-editor.org/rfc/rfc2256.html#section-7.10
            # TODO: properly manage the situation where one wants to
            # remove the last member of a group
            group.members = [member for member in group.members if member != self]
            LDAPBackend.instance.save(group)

        if "new_groups" in data:
            self.state[data["group_attr"]] = data["new_groups"]


class Group(canaille.core.models.Group, LDAPObject):
    attribute_map: ClassVar[dict[str, str] | None] = {
        "id": "entryUUID",
        "created": "createTimestamp",
        "last_modified": "modifyTimestamp",
        "display_name": "cn",
        "members": "member",
        "description": "description",
    }


class Client(canaille.oidc.models.Client, LDAPObject):
    ldap_object_class = ["oauthClient"]
    base = "ou=clients,ou=oauth"
    rdn_attribute = "oauthClientID"

    client_info_attributes_map: ClassVar[dict[str, str]] = {
        "client_id": "oauthClientID",
        "client_secret": "oauthClientSecret",
        "client_id_issued_at": "oauthIssueDate",
        "client_secret_expires_at": "oauthClientSecretExpDate",
    }

    client_metadata_attributes_map: ClassVar[dict[str, str]] = {
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
        "jwks": "oauthJWK",
        "token_endpoint_auth_method": "oauthTokenEndpointAuthMethod",
        "software_id": "oauthSoftwareID",
        "software_version": "oauthSoftwareVersion",
        "token_endpoint_auth_signing_alg": "oauthTokenEndpointAuthSigningAlg",
        "sector_identifier_uri": "oauthSectorIdentifierURI",
        "subject_type": "oauthSubjectType",
        "application_type": "oauthApplicationType",
        "id_token_signed_response_alg": "oauthIdTokenSignedResponseAlg",
        "id_token_encrypted_response_alg": "oauthIdTokenEncryptedResponseAlg",
        "id_token_encrypted_response_enc": "oauthIdTokenEncryptedResponseEnc",
        "userinfo_signed_response_alg": "oauthUserinfoSignedResponseAlg",
        "userinfo_encrypted_response_alg": "oauthUserinfoEncryptedResponseAlg",
        "userinfo_encrypted_response_enc": "oauthUserinfoEncryptedResponseEnc",
        "default_max_age": "oauthDefaultMaxAge",
        "require_auth_time": "oauthRequireAuthTime",
        "default_acr_values": "oauthDefaultAcrValue",
        "initiate_login_uri": "oauthInitiateLoginURI",
        "request_object_signing_alg": "oauthRequestObjectSigningAlg",
        "request_object_encryption_alg": "oauthRequestObjectEncryptionAlg",
        "request_object_encryption_enc": "oauthRequestObjectEncryptionEnc",
        "request_uris": "oauthRequestURI",
    }

    attribute_map: ClassVar[dict[str, str] | None] = {
        "id": "entryUUID",
        "created": "createTimestamp",
        "last_modified": "modifyTimestamp",
        "trusted": "oauthPreconsent",
        # post_logout_redirect_uris is not yet supported by authlib
        "post_logout_redirect_uris": "oauthPostLogoutRedirectURI",
        "audience": "oauthAudience",
        **client_info_attributes_map,
        **client_metadata_attributes_map,
    }


class AuthorizationCode(canaille.oidc.models.AuthorizationCode, LDAPObject):
    ldap_object_class = ["oauthAuthorizationCode"]
    base = "ou=authorizations,ou=oauth"
    rdn_attribute = "oauthAuthorizationCodeID"
    attribute_map: ClassVar[dict[str, str] | None] = {
        "id": "entryUUID",
        "created": "createTimestamp",
        "last_modified": "modifyTimestamp",
        "authorization_code_id": "oauthAuthorizationCodeID",
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


class Token(canaille.oidc.models.Token, LDAPObject):
    ldap_object_class = ["oauthToken"]
    base = "ou=tokens,ou=oauth"
    rdn_attribute = "oauthTokenID"
    attribute_map: ClassVar[dict[str, str] | None] = {
        "id": "entryUUID",
        "created": "createTimestamp",
        "last_modified": "modifyTimestamp",
        "token_id": "oauthTokenID",
        "access_token": "oauthAccessToken",
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


class Consent(canaille.oidc.models.Consent, LDAPObject):
    ldap_object_class = ["oauthConsent"]
    base = "ou=consents,ou=oauth"
    rdn_attribute = "cn"
    attribute_map: ClassVar[dict[str, str] | None] = {
        "id": "entryUUID",
        "created": "createTimestamp",
        "last_modified": "modifyTimestamp",
        "consent_id": "cn",
        "subject": "oauthSubject",
        "client": "oauthClient",
        "scope": "oauthScope",
        "issue_date": "oauthIssueDate",
        "revokation_date": "oauthRevokationDate",
    }
