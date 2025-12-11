from typing import ClassVar

import ldap.filter
from blinker import signal

import canaille.core.models

from ..backend import LDAPBackend
from ..ldapobject import LDAPObject


class User(canaille.core.models.User, LDAPObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        signal("before_user_save").connect(self.before_save, sender=self)
        signal("after_user_save").connect(self.after_save, sender=self)

    def get_password_hash(self):
        return self.password

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
        "owners": "owner",
        "description": "description",
    }
