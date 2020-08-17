import ldap
import time
import datetime
from flask import g
from authlib.common.encoding import json_loads, json_dumps
from authlib.oauth2.rfc6749 import (
    ClientMixin,
    TokenMixin,
    AuthorizationCodeMixin,
)


class LDAPObjectHelper:
    _object_class_by_name = None
    _attribute_type_by_name = None
    may = None
    must = None
    base = None
    id = None

    def __init__(self, dn=None, **kwargs):
        self.attrs = {}
        for k, v in kwargs.items():
            self.attrs[k] = [v] if not isinstance(v, list) else v
        self.attrs.setdefault("objectClass", self.objectClass)

        by_name = self.ocs_by_name()
        ocs = [by_name[name] for name in self.objectClass]
        self.may = []
        self.must = []
        for oc in ocs:
            self.may.extend(oc.may)
            self.must.extend(oc.must)

    @property
    def dn(self):
        if not self.id in self.attrs:
            return None
        return f"{self.id}={self.attrs[self.id][0]},{self.base}"

    @classmethod
    def ocs_by_name(cls):
        if cls._object_class_by_name:
            return cls._object_class_by_name

        res = g.ldap.search_s(
            "cn=subschema", ldap.SCOPE_BASE, "(objectclass=*)", ["*", "+"]
        )
        subschema_entry = res[0]
        subschema_subentry = ldap.cidict.cidict(subschema_entry[1])
        subschema = ldap.schema.SubSchema(subschema_subentry)
        object_class_oids = subschema.listall(ldap.schema.models.ObjectClass)
        cls._object_class_by_name = {}
        for oid in object_class_oids:
            oc = subschema.get_obj(ldap.schema.models.ObjectClass, oid)
            for name in oc.names:
                cls._object_class_by_name[name] = oc

        return cls._object_class_by_name

    @classmethod
    def attr_type_by_name(cls):
        if cls._attribute_type_by_name:
            return cls._attribute_type_by_name

        res = g.ldap.search_s(
            "cn=subschema", ldap.SCOPE_BASE, "(objectclass=*)", ["*", "+"]
        )
        subschema_entry = res[0]
        subschema_subentry = ldap.cidict.cidict(subschema_entry[1])
        subschema = ldap.schema.SubSchema(subschema_subentry)
        attribute_type_oids = subschema.listall(ldap.schema.models.AttributeType)
        cls._attribute_type_by_name = {}
        for oid in attribute_type_oids:
            oc = subschema.get_obj(ldap.schema.models.AttributeType, oid)
            for name in oc.names:
                cls._attribute_type_by_name[name] = oc

        return cls._attribute_type_by_name

    def save(self):
        try:
            match = bool(g.ldap.search_s(self.dn, ldap.SCOPE_SUBTREE))
        except ldap.NO_SUCH_OBJECT:
            match = False

        if match:
            attributes = [
                (ldap.MOD_REPLACE, k, [elt.encode("utf-8") for elt in v])
                for k, v in self.attrs.items()
            ]
            g.ldap.modify_s(self.dn, attributes)

        else:
            attributes = [
                (k, [elt.encode("utf-8") for elt in v]) for k, v in self.attrs.items()
            ]
            g.ldap.add_s(self.dn, attributes)

    @classmethod
    def get(cls, dn):
        if "=" not in dn:
            dn = f"{cls.id}={dn},{cls.base}"
        result = g.ldap.search_s(dn, ldap.SCOPE_SUBTREE)

        if not result:
            return None

        o = cls(
            **{k: [elt.decode("utf-8") for elt in v] for k, v in result[0][1].items()}
        )

        return o

    @classmethod
    def filter(cls, base=None, **kwargs):
        class_filter = "".join([f"(objectClass={oc})" for oc in cls.objectClass])
        arg_filter = "".join(f"({k}={v})" for k, v in kwargs.items())
        ldapfilter = f"(&{class_filter}{arg_filter})"
        result = g.ldap.search_s(base or cls.base, ldap.SCOPE_SUBTREE, ldapfilter)

        return [
            cls(**{k: [elt.decode("utf-8") for elt in v] for k, v in args.items()},)
            for _, args in result
        ]

    def __getattr__(self, name):
        if (not self.may or name not in self.may) and (
            not self.must or name not in self.must
        ):
            return super().__getattribute__(name)

        if (
            not self.attr_type_by_name()
            or not self.attr_type_by_name()[name].single_value
        ):
            return self.attrs.get(name, [])

        return self.attrs.get(name, [None])[0]

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if not isinstance(value, list):
            value = [value]
        if (self.may and name in self.may) or (self.must and name in self.must):
            if self.attr_type_by_name()[name].single_value:
                self.attrs[name] = [value]
            else:
                self.attrs[name] = value


class User(LDAPObjectHelper):
    objectClass = ["person"]
    base = "ou=users,dc=mydomain,dc=tld"
    id = "cn"

    def __repr__(self):
        return self.cn[0]

    def check_password(self, password):
        return password == "valid"


class Client(LDAPObjectHelper, ClientMixin):
    objectClass = ["oauthClient"]
    base = "ou=clients,dc=mydomain,dc=tld"
    id = "oauthClientID"

    def get_client_id(self):
        return self.oauthClientID

    def get_default_redirect_uri(self):
        return self.oauthRedirectURI

    def get_allowed_scope(self, scope):
        return self.oauthScope

    def check_redirect_uri(self, redirect_uri):
        return redirect_uri in self.oauthRedirectURI

    def has_client_secret(self):
        return bool(self.oauthClientSecret)

    def check_client_secret(self, client_secret):
        return client_secret == self.oauthClientSecret

    def check_token_endpoint_auth_method(self, method):
        return method == self.oauthTokenEndpointAuthMethod

    def check_response_type(self, response_type):
        return response_type in self.oauthResponseType

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

    @property
    def client_metadata(self):
        if "client_metadata" in self.__dict__:
            return self.__dict__["client_metadata"]
        if self._client_metadata:
            data = json_loads(self._client_metadata)
            self.__dict__["client_metadata"] = data
            return data
        return {}

    def set_client_metadata(self, value):
        self._client_metadata = json_dumps(value)

    @property
    def redirect_uris(self):
        return self.client_metadata.get("redirect_uris", [])

    @property
    def token_endpoint_auth_method(self):
        return self.client_metadata.get(
            "token_endpoint_auth_method", "client_secret_basic"
        )


class AuthorizationCode(LDAPObjectHelper, AuthorizationCodeMixin):
    objectClass = ["oauthAuthorizationCode"]
    base = "ou=authorizations,dc=mydomain,dc=tld"
    id = "oauthCode"

    def get_redirect_uri(self):
        return Client.get(self.authzClientID).oauthRedirectURI

    def get_scope(self):
        return self.oauth2ScopeValue

    def is_refresh_token_active(self):
        if self.revoked:
            return False
        expires_at = self.issued_at + self.expires_in * 2
        return expires_at >= time.time()

    def get_client_id(self):
        return self.client_id

    def get_expires_in(self):
        return self.expires_in

    def get_expires_at(self):
        return self.issued_at + self.expires_in


class Token(LDAPObjectHelper, TokenMixin):
    objectClass = ["oauthToken"]
    base = "ou=tokens,dc=mydomain,dc=tld"
    id = "oauthAccessToken"

    def get_client_id(self):
        return self.authzClientID

    def get_scope(self):
        return " ".join(self.oauthScope)

    def get_expires_in(self):
        return int(self.oauthTokenLifetime)

    def get_expires_at(self):
        issue_date = datetime.datetime.strptime(self.oauthIssueDate, "%Y%m%d%H%M%SZ")
        issue_timestamp = (issue_date - datetime.datetime(1970, 1, 1)).total_seconds()
        return issue_timestamp + int(self.oauthTokenLifetime)

    def is_refresh_token_active(self):
        if self.revoked:
            return False
        expires_at = self.issued_at + self.expires_in * 2
        return expires_at >= time.time()
