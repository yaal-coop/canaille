import datetime
import ldap
import uuid
from authlib.oauth2.rfc6749 import (
    ClientMixin,
    TokenMixin,
    AuthorizationCodeMixin,
    util,
)
from flask import current_app, session
from .ldaputils import LDAPObject


class User(LDAPObject):
    id = "cn"
    admin = False
    moderator = False
    _groups = []

    @classmethod
    def get(cls, login=None, dn=None, filter=None, conn=None):
        conn = conn or cls.ldap()

        if login:
            filter = current_app.config["LDAP"].get("USER_FILTER").format(login=login)

        user = super().get(dn, filter, conn)

        admin_filter = current_app.config["LDAP"].get("ADMIN_FILTER")
        moderator_filter = current_app.config["LDAP"].get("USER_ADMIN_FILTER")
        if (
            admin_filter
            and user
            and user.dn
            and conn.search_s(user.dn, ldap.SCOPE_SUBTREE, admin_filter)
        ):

            user.admin = True
            user.moderator = True

        elif (
            moderator_filter
            and user
            and user.dn
            and conn.search_s(user.dn, ldap.SCOPE_SUBTREE, moderator_filter)
        ):

            user.moderator = True

        if user:
            user.load_groups(conn=conn)

        return user

    def load_groups(self, conn=None):
        try:
            group_filter = current_app.config["LDAP"]["GROUP_USER_FILTER"].format(
                user=self
            )
            self._groups = Group.filter(filter=group_filter, conn=conn)
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
                self.dn, None, password.encode("utf-8"),
            )

        except ldap.LDAPError:
            return False

        return True

    @property
    def name(self):
        return self.cn[0]

    @property
    def groups(self):
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


class Group(LDAPObject):
    id = "cn"

    @classmethod
    def available_groups(cls, conn=None):
        conn = conn or cls.ldap()
        try:
            attribute = current_app.config["LDAP"]["GROUP_NAME_ATTRIBUTE"]
            object_class = current_app.config["LDAP"]["GROUP_CLASS"]
        except KeyError:
            return []

        groups = cls.filter(objectClass=object_class, conn=conn)
        Group.attr_type_by_name(conn=conn)
        return [(group[attribute][0], group.dn) for group in groups]

    @property
    def name(self):
        attribute = current_app.config["LDAP"].get("GROUP_NAME_ATTRIBUTE")
        return self[attribute][0]

    def get_members(self, conn=None):
        return [User.get(dn=user_dn, conn=conn) for user_dn in self.member]

    def add_member(self, user, conn=None):
        self.member = self.member + [user.dn]
        self.save(conn=conn)

    def remove_member(self, user, conn=None):
        self.member = [m for m in self.member if m != user.dn]
        self.save(conn=conn)


class Client(LDAPObject, ClientMixin):
    object_class = ["oauthClient"]
    base = "ou=clients,ou=oauth"
    id = "oauthClientID"

    @property
    def issue_date(self):
        return (
            datetime.datetime.strptime(self.oauthIssueDate, "%Y%m%d%H%M%SZ")
            if self.oauthIssueDate
            else None
        )

    def get_client_id(self):
        return self.oauthClientID

    def get_default_redirect_uri(self):
        return self.oauthRedirectURIs[0]

    def get_allowed_scope(self, scope):
        return util.list_to_scope(self.oauthScope)

    def check_redirect_uri(self, redirect_uri):
        return redirect_uri in self.oauthRedirectURIs

    def has_client_secret(self):
        return bool(self.oauthClientSecret)

    def check_client_secret(self, client_secret):
        return client_secret == self.oauthClientSecret

    def check_token_endpoint_auth_method(self, method):
        return method == self.oauthTokenEndpointAuthMethod

    def check_response_type(self, response_type):
        return all(r in self.oauthResponseType for r in response_type.split(" "))

    def check_grant_type(self, grant_type):
        return grant_type in self.oauthGrantType

    @property
    def client_info(self):
        return dict(
            client_id=self.client_id,
            client_secret=self.client_secret,
            client_id_issued_at=self.client_id_issued_at,
            client_secret_expires_at=self.client_secret_expires_at,
        )


class AuthorizationCode(LDAPObject, AuthorizationCodeMixin):
    object_class = ["oauthAuthorizationCode"]
    base = "ou=authorizations,ou=oauth"
    id = "oauthCode"

    @property
    def issue_date(self):
        return (
            datetime.datetime.strptime(self.oauthIssueDate, "%Y%m%d%H%M%SZ")
            if self.oauthIssueDate
            else None
        )

    def get_redirect_uri(self):
        return self.oauthRedirectURI

    def get_scope(self):
        return self.oauthScope

    def get_nonce(self):
        return self.oauthNonce

    def is_expired(self):
        return (
            datetime.datetime.strptime(self.oauthAuthorizationDate, "%Y%m%d%H%M%SZ")
            + datetime.timedelta(seconds=int(self.oauthAuthorizationLifetime))
            < datetime.datetime.now()
        )

    def get_auth_time(self):
        auth_time = datetime.datetime.strptime(
            self.oauthAuthorizationDate, "%Y%m%d%H%M%SZ"
        )
        return int((auth_time - datetime.datetime(1970, 1, 1)).total_seconds())


class Token(LDAPObject, TokenMixin):
    object_class = ["oauthToken"]
    base = "ou=tokens,ou=oauth"
    id = "oauthAccessToken"

    @property
    def issue_date(self):
        return (
            datetime.datetime.strptime(self.oauthIssueDate, "%Y%m%d%H%M%SZ")
            if self.oauthIssueDate
            else None
        )

    @property
    def expire_date(self):
        return datetime.datetime.strptime(
            self.oauthIssueDate, "%Y%m%d%H%M%SZ"
        ) + datetime.timedelta(seconds=int(self.oauthTokenLifetime))

    @property
    def revoked(self):
        return bool(self.oauthRevokationDate)

    def get_client_id(self):
        return Client.get(self.oauthClient).oauthClientID

    def get_scope(self):
        return " ".join(self.oauthScope)

    def get_expires_in(self):
        return int(self.oauthTokenLifetime)

    def get_issued_at(self):
        issue_date = datetime.datetime.strptime(self.oauthIssueDate, "%Y%m%d%H%M%SZ")
        return int((issue_date - datetime.datetime(1970, 1, 1)).total_seconds())

    def get_expires_at(self):
        issue_date = datetime.datetime.strptime(self.oauthIssueDate, "%Y%m%d%H%M%SZ")
        issue_timestamp = (issue_date - datetime.datetime(1970, 1, 1)).total_seconds()
        return int(issue_timestamp) + int(self.oauthTokenLifetime)

    def is_refresh_token_active(self):
        if self.oauthRevokationDate:
            return False

        return self.expire_date >= datetime.datetime.now()

    def is_expired(self):
        return (
            datetime.datetime.strptime(self.oauthIssueDate, "%Y%m%d%H%M%SZ")
            + datetime.timedelta(seconds=int(self.oauthTokenLifetime))
            < datetime.datetime.now()
        )


class Consent(LDAPObject):
    object_class = ["oauthConsent"]
    base = "ou=consents,ou=oauth"
    id = "cn"

    def __init__(self, *args, **kwargs):
        if "cn" not in kwargs:
            kwargs["cn"] = str(uuid.uuid4())

        super().__init__(*args, **kwargs)

    @property
    def issue_date(self):
        return (
            datetime.datetime.strptime(self.oauthIssueDate, "%Y%m%d%H%M%SZ")
            if self.oauthIssueDate
            else None
        )

    @property
    def revokation_date(self):
        return datetime.datetime.strptime(self.oauthRevokationDate, "%Y%m%d%H%M%SZ")

    def revoke(self):
        self.oauthRevokationDate = datetime.datetime.now().strftime("%Y%m%d%H%M%SZ")
        self.save()

        tokens = Token.filter(
            oauthClient=self.oauthClient, oauthSubject=self.oauthSubject,
        )
        for t in tokens:
            if t.revoked or any(
                scope not in t.oauthScope[0] for scope in self.oauthScope
            ):
                continue

            t.oauthRevokationDate = self.oauthRevokationDate
            t.save()
