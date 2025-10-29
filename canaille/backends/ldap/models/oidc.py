from typing import ClassVar

import canaille.oidc.models

from ..ldapobject import LDAPObject


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
        "require_signed_request_object": "oauthRequireSignedRequestObject",
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
        "auth_time": "oauthAuthTime",
        "acr": "oauthACR",
        "amr": "oauthAMR",
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
