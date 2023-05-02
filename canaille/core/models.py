import ldap.filter
from canaille.backends.ldap.ldapobject import LDAPObject
from flask import current_app
from flask import session


class User(LDAPObject):
    DEFAULT_OBJECT_CLASS = "inetOrgPerson"
    DEFAULT_FILTER = "(|(uid={login})(mail={login}))"
    DEFAULT_ID_ATTRIBUTE = "cn"

    attribute_table = {
        "id": "dn",
        "user_name": "uid",
        "password": "userPassword",
        "preferred_language": "preferredLanguage",
        "family_name": "sn",
        "given_name": "givenName",
        "formatted_name": "cn",
        "display_name": "displayName",
        "email": "mail",
        "phone_number": "telephoneNumber",
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
    }

    def __init__(self, *args, **kwargs):
        self.read = set()
        self.write = set()
        self.permissions = set()
        super().__init__(*args, **kwargs)

    @classmethod
    def get_from_login(cls, login=None, **kwargs):
        filter = (
            (
                current_app.config["BACKENDS"]["LDAP"]
                .get("USER_FILTER", User.DEFAULT_FILTER)
                .format(login=ldap.filter.escape_filter_chars(login))
            )
            if login
            else None
        )
        return cls.get(filter=filter, **kwargs)

    @classmethod
    def get(cls, **kwargs):
        user = super().get(**kwargs)
        if user:
            user.load_permissions()

        return user

    @classmethod
    def acl_filter_to_ldap_filter(cls, filter_):
        if isinstance(filter_, dict):
            # not super generic, but how can we improve this? ¯\_(ツ)_/¯
            if "groups" in filter_ and "=" not in filter_.get("groups"):
                filter_["groups"] = Group.dn_for(filter_["groups"])

            base = "".join(
                f"({cls.attribute_table.get(key, key)}={value})"
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
    def authenticate(cls, login, password, signin=False):
        user = User.get_from_login(login)
        if not user or not user.check_password(password):
            return None

        if signin:
            user.login()

        return user

    def login(self):
        try:
            previous = (
                session["user_id"]
                if isinstance(session["user_id"], list)
                else [session["user_id"]]
            )
            session["user_id"] = previous + [self.id]
        except KeyError:
            session["user_id"] = [self.id]

    @classmethod
    def logout(self):
        try:
            session["user_id"].pop()
            if not session["user_id"]:
                del session["user_id"]
        except (IndexError, KeyError):
            pass

    def has_password(self):
        return bool(self.password)

    def check_password(self, password):
        conn = ldap.initialize(current_app.config["BACKENDS"]["LDAP"]["URI"])

        conn.set_option(
            ldap.OPT_NETWORK_TIMEOUT,
            current_app.config["BACKENDS"]["LDAP"].get("TIMEOUT"),
        )

        try:
            conn.simple_bind_s(self.id, password)
            return True
        except ldap.INVALID_CREDENTIALS:
            return False
        finally:
            conn.unbind_s()

    def set_password(self, password):
        conn = self.ldap_connection()
        conn.passwd_s(
            self.id,
            None,
            password.encode("utf-8"),
        )

    def reload(self):
        super().reload()
        self.load_permissions()

    def save(self, *args, **kwargs):
        group_attr = self.attribute_table.get("groups", "groups")
        new_groups = self.changes.get(group_attr)
        if not new_groups:
            return super().save(*args, **kwargs)

        old_groups = self.attrs.get(group_attr) or []
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

        self.attrs[group_attr] = new_groups

    def load_permissions(self):
        conn = self.ldap_connection()

        for access_group_name, details in current_app.config["ACL"].items():
            filter_ = self.acl_filter_to_ldap_filter(details.get("FILTER"))
            if not filter_ or (
                self.id and conn.search_s(self.id, ldap.SCOPE_SUBTREE, filter_)
            ):
                self.permissions |= set(details.get("PERMISSIONS", []))
                self.read |= set(details.get("READ", []))
                self.write |= set(details.get("WRITE", []))

    def can_read(self, field):
        return field in self.read | self.write

    @property
    def can_edit_self(self):
        return "edit_self" in self.permissions

    @property
    def can_use_oidc(self):
        return "use_oidc" in self.permissions

    @property
    def can_manage_users(self):
        return "manage_users" in self.permissions

    @property
    def can_manage_groups(self):
        return "manage_groups" in self.permissions

    @property
    def can_manage_oidc(self):
        return "manage_oidc" in self.permissions

    @property
    def can_delete_account(self):
        return "delete_account" in self.permissions

    @property
    def can_impersonate_users(self):
        return "impersonate_users" in self.permissions


class Group(LDAPObject):
    DEFAULT_OBJECT_CLASS = "groupOfNames"
    DEFAULT_ID_ATTRIBUTE = "cn"
    DEFAULT_NAME_ATTRIBUTE = "cn"

    attribute_table = {
        "id": "dn",
        "display_name": "cn",
        "members": "member",
        "description": "description",
    }

    @property
    def display_name(self):
        attribute = current_app.config["BACKENDS"]["LDAP"].get(
            "GROUP_NAME_ATTRIBUTE", Group.DEFAULT_NAME_ATTRIBUTE
        )
        return self[attribute][0]
