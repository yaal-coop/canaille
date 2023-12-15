import canaille.core.models
import canaille.oidc.models
import ldap.filter
from flask import current_app
from ldap.controls import DecodeControlTuples
from ldap.controls.ppolicy import PasswordPolicyControl
from ldap.controls.ppolicy import PasswordPolicyError

from .backend import Backend
from .ldapobject import LDAPObject


class User(canaille.core.models.User, LDAPObject):
    DEFAULT_OBJECT_CLASS = "inetOrgPerson"
    DEFAULT_FILTER = "(|(uid={{ login }})(mail={{ login }}))"
    DEFAULT_RDN = "cn"

    attribute_map = {
        "id": "dn",
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
        "last_modified": "modifyTimestamp",
        "groups": "memberOf",
        "lock_date": "pwdEndTime",
    }

    @classmethod
    def get_from_login(cls, login=None, **kwargs):
        raw_filter = current_app.config["BACKENDS"]["LDAP"].get(
            "USER_FILTER", User.DEFAULT_FILTER
        )
        filter = (
            (
                current_app.jinja_env.from_string(raw_filter).render(
                    login=ldap.filter.escape_filter_chars(login)
                )
            )
            if login
            else None
        )
        return cls.get(filter=filter, **kwargs)

    @classmethod
    def acl_filter_to_ldap_filter(cls, filter_):
        if isinstance(filter_, dict):
            # not super generic, but how can we improve this? ¯\_(ツ)_/¯
            if "groups" in filter_ and "=" not in filter_.get("groups"):
                filter_["groups"] = Group.dn_for(filter_["groups"])

            base = "".join(
                f"({cls.python_attribute_to_ldap(key)}={value})"
                for key, value in filter_.items()
            )
            return f"(&{base})" if len(filter_) > 1 else base

        if isinstance(filter_, list):
            return (
                "(|"
                + "".join(cls.acl_filter_to_ldap_filter(mapping) for mapping in filter_)
                + ")"
            )

        return filter_

    @classmethod
    def get(cls, *args, **kwargs):
        user = super().get(*args, **kwargs)
        if user:
            user.load_permissions()

        return user

    @property
    def identifier(self):
        return self.rdn_value

    def has_password(self):
        return bool(self.password)

    def check_password(self, password):
        conn = ldap.initialize(current_app.config["BACKENDS"]["LDAP"]["URI"])

        conn.set_option(
            ldap.OPT_NETWORK_TIMEOUT,
            current_app.config["BACKENDS"]["LDAP"].get("TIMEOUT"),
        )

        message = None
        try:
            res = conn.simple_bind_s(
                self.id, password, serverctrls=[PasswordPolicyControl()]
            )
            controls = res[3]
            result = True
        except ldap.INVALID_CREDENTIALS as exc:
            controls = DecodeControlTuples(exc.args[0]["ctrls"])
            result = False
        finally:
            conn.unbind_s()

        for control in controls:

            def gettext(x):
                return x

            if (
                control.controlType == PasswordPolicyControl.controlType
                and control.error == PasswordPolicyError.namedValues["accountLocked"]
            ):
                message = gettext("Your account has been locked.")
            elif (
                control.controlType == PasswordPolicyControl.controlType
                and control.error == PasswordPolicyError.namedValues["changeAfterReset"]
            ):
                message = gettext("You should change your password.")

        return result, message

    def set_password(self, password):
        conn = Backend.get().connection
        conn.passwd_s(
            self.id,
            None,
            password.encode("utf-8"),
        )

    def reload(self):
        super().reload()
        self.load_permissions()

    def save(self, *args, **kwargs):
        group_attr = self.python_attribute_to_ldap("groups")
        new_groups = self.changes.get(group_attr)
        if not new_groups:
            return super().save(*args, **kwargs)

        old_groups = self.state.get(group_attr) or []
        new_groups = [
            v if isinstance(v, Group) else Group.get(id=v) for v in new_groups
        ]
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

    def load_permissions(self):
        conn = Backend.get().connection
        self.permissions = set()
        self.read = set()
        self.write = set()

        for access_group_name, details in current_app.config.get("ACL", {}).items():
            filter_ = self.acl_filter_to_ldap_filter(details.get("FILTER"))
            if not filter_ or (
                self.id and conn.search_s(self.id, ldap.SCOPE_SUBTREE, filter_)
            ):
                self.permissions |= set(details.get("PERMISSIONS", []))
                self.read |= set(details.get("READ", []))
                self.write |= set(details.get("WRITE", []))


class Group(canaille.core.models.Group, LDAPObject):
    DEFAULT_OBJECT_CLASS = "groupOfNames"
    DEFAULT_RDN = "cn"
    DEFAULT_NAME_ATTRIBUTE = "cn"
    DEFAULT_USER_FILTER = "member={user.id}"

    attribute_map = {
        "id": "dn",
        "display_name": "cn",
        "members": "member",
        "description": "description",
    }

    @property
    def identifier(self):
        return self.rdn_value

    @property
    def display_name(self):
        attribute = current_app.config["BACKENDS"]["LDAP"].get(
            "GROUP_NAME_ATTRIBUTE", Group.DEFAULT_NAME_ATTRIBUTE
        )
        return getattr(self, attribute)[0]


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
        "id": "dn",
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
        "id": "dn",
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
        "id": "dn",
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
        "id": "dn",
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
