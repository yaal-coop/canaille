import ldap.filter

import canaille.core.models
import canaille.oidc.models

from .backend import Backend
from .ldapobject import LDAPObject


class User(canaille.core.models.User, LDAPObject):
    attribute_map = {
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
    }

    def match_filter(self, filter):
        if isinstance(filter, str):
            conn = Backend.get().connection
            return self.dn and conn.search_s(self.dn, ldap.SCOPE_SUBTREE, filter)

        return super().match_filter(filter)

    @property
    def identifier(self):
        return self.rdn_value

    def save(self, *args, **kwargs):
        group_attr = self.python_attribute_to_ldap("groups")
        new_groups = self.changes.get(group_attr)
        if not new_groups:
            return super().save(*args, **kwargs)

        old_groups = self.state.get(group_attr) or []
        new_groups = [v if isinstance(v, Group) else Group.get(v) for v in new_groups]
        to_add = set(new_groups) - set(old_groups)
        to_del = set(old_groups) - set(new_groups)

        del self.changes[group_attr]
        super().save(*args, **kwargs)

        for group in to_add:
            group.members = group.members + [self]
            group.save()

        for group in to_del:
            group.members = [member for member in group.members if member != self]
            group.save()

        self.state[group_attr] = new_groups


class Group(canaille.core.models.Group, LDAPObject):
    attribute_map = {
        "id": "entryUUID",
        "created": "createTimestamp",
        "last_modified": "modifyTimestamp",
        "display_name": "cn",
        "members": "member",
        "description": "description",
    }

    @property
    def identifier(self):
        return self.rdn_value


class Client(canaille.oidc.models.Client, LDAPObject):
    ldap_object_class = ["oauthClient"]
    base = "ou=clients,ou=oauth"
    rdn_attribute = "oauthClientID"

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

    attribute_map = {
        "id": "entryUUID",
        "created": "createTimestamp",
        "last_modified": "modifyTimestamp",
        "preconsent": "oauthPreconsent",
        # post_logout_redirect_uris is not yet supported by authlib
        "post_logout_redirect_uris": "oauthPostLogoutRedirectURI",
        "audience": "oauthAudience",
        **client_info_attributes,
        **client_metadata_attributes,
    }

    @property
    def identifier(self):
        return self.rdn_value


class AuthorizationCode(canaille.oidc.models.AuthorizationCode, LDAPObject):
    ldap_object_class = ["oauthAuthorizationCode"]
    base = "ou=authorizations,ou=oauth"
    rdn_attribute = "oauthAuthorizationCodeID"
    attribute_map = {
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

    @property
    def identifier(self):
        return self.rdn_value


class Token(canaille.oidc.models.Token, LDAPObject):
    ldap_object_class = ["oauthToken"]
    base = "ou=tokens,ou=oauth"
    rdn_attribute = "oauthTokenID"
    attribute_map = {
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

    @property
    def identifier(self):
        return self.rdn_value


class Consent(canaille.oidc.models.Consent, LDAPObject):
    ldap_object_class = ["oauthConsent"]
    base = "ou=consents,ou=oauth"
    rdn_attribute = "cn"
    attribute_map = {
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

    @property
    def identifier(self):
        return self.rdn_value
