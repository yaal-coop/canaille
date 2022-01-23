import ldap.filter
from flask import current_app
from flask import session

from .ldap_backend.ldapobject import LDAPObject


class User(LDAPObject):
    DEFAULT_OBJECT_CLASS = "inetOrgPerson"
    DEFAULT_FILTER = "(|(uid={login})(mail={login}))"
    DEFAULT_ID_ATTRIBUTE = "cn"

    def __init__(self, *args, **kwargs):
        self.read = set()
        self.write = set()
        self.permissions = set()
        self._groups = None
        super().__init__(*args, **kwargs)

    @classmethod
    def get(cls, login=None, dn=None, filter=None, conn=None):
        conn = conn or cls.ldap()

        if login:
            filter = (
                current_app.config["LDAP"]
                .get("USER_FILTER", User.DEFAULT_FILTER)
                .format(login=ldap.filter.escape_filter_chars(login))
            )

        user = super().get(dn, filter, conn)
        if user:
            user.load_permissions(conn)

        return user

    def load_groups(self, conn=None):
        try:
            group_filter = (
                current_app.config["LDAP"]
                .get("GROUP_USER_FILTER", Group.DEFAULT_USER_FILTER)
                .format(user=self)
            )
            escaped_group_filter = ldap.filter.escape_filter_chars(group_filter)
            self._groups = Group.filter(filter=escaped_group_filter, conn=conn)
        except KeyError:
            pass

    @classmethod
    def authenticate(cls, login, password, signin=False):
        user = User.get(login)
        if not user or not user.check_password(password):
            return None

        if signin:
            user.login()

        return user

    def login(self):
        try:
            previous = (
                session["user_dn"]
                if isinstance(session["user_dn"], list)
                else [session["user_dn"]]
            )
            session["user_dn"] = previous + [self.dn]
        except KeyError:
            session["user_dn"] = [self.dn]

    @classmethod
    def logout(self):
        try:
            if isinstance(session["user_dn"], list):
                session["user_dn"].pop()
            else:
                del session["user_dn"]
        except (IndexError, KeyError):
            pass

    def has_password(self):
        return bool(self.userPassword)

    def check_password(self, password):
        conn = ldap.initialize(current_app.config["LDAP"]["URI"])

        if current_app.config["LDAP"].get("TIMEOUT"):
            conn.set_option(
                ldap.OPT_NETWORK_TIMEOUT, current_app.config["LDAP"]["TIMEOUT"]
            )

        try:
            conn.simple_bind_s(self.dn, password)
            return True
        except ldap.INVALID_CREDENTIALS:
            return False
        finally:
            conn.unbind_s()

    def set_password(self, password, conn=None):
        conn = conn or self.ldap()

        try:
            conn.passwd_s(
                self.dn,
                None,
                password.encode("utf-8"),
            )

        except ldap.LDAPError:
            return False

        return True

    @property
    def name(self):
        return self.cn[0]

    @property
    def groups(self):
        if self._groups is None:
            self.load_groups()
        return self._groups

    def set_groups(self, values, conn=None):
        before = self._groups
        after = [
            v if isinstance(v, Group) else Group.get(dn=v, conn=conn) for v in values
        ]
        to_add = set(after) - set(before)
        to_del = set(before) - set(after)
        for group in to_add:
            group.add_member(self, conn=conn)
        for group in to_del:
            group.remove_member(self, conn=conn)
        self._groups = after

    def load_permissions(self, conn=None):
        conn = conn or self.ldap()

        for access_group_name, details in current_app.config["ACL"].items():
            if not details.get("FILTER") or (
                self.dn
                and conn.search_s(self.dn, ldap.SCOPE_SUBTREE, details["FILTER"])
            ):
                self.permissions |= set(details.get("PERMISSIONS", []))
                self.read |= set(details.get("READ", []))
                self.write |= set(details.get("WRITE", []))

    def can_read(self, field):
        return field in self.read | self.write

    def can_writec(self, field):
        return field in self.write

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
    DEFAULT_USER_FILTER = "member={user.dn}"

    @classmethod
    def available_groups(cls, conn=None):
        conn = conn or cls.ldap()
        try:
            attribute = current_app.config["LDAP"].get(
                "GROUP_NAME_ATTRIBUTE", Group.DEFAULT_NAME_ATTRIBUTE
            )
            object_class = current_app.config["LDAP"].get(
                "GROUP_CLASS", Group.DEFAULT_OBJECT_CLASS
            )
        except KeyError:
            return []

        groups = cls.filter(objectClass=object_class, conn=conn)
        Group.ldap_object_attributes(conn=conn)
        return [(group[attribute][0], group.dn) for group in groups]

    @property
    def name(self):
        attribute = current_app.config["LDAP"].get(
            "GROUP_NAME_ATTRIBUTE", Group.DEFAULT_NAME_ATTRIBUTE
        )
        return self[attribute][0]

    def get_members(self, conn=None):
        return [
            User.get(dn=user_dn, conn=conn)
            for user_dn in self.member
            if User.get(dn=user_dn, conn=conn)
        ]

    def add_member(self, user, conn=None):
        self.member = self.member + [user.dn]
        self.save(conn=conn)

    def remove_member(self, user, conn=None):
        self.member = [m for m in self.member if m != user.dn]
        self.save(conn=conn)
