import ldap
from pprint import pprint


l = ldap.initialize("ldap://ldap")
l.simple_bind_s("cn=admin,dc=mydomain,dc=tld", "admin")


class LDAPObjectHelper:
    _object_class_by_name = None
    may = None
    must = None

    def __init__(self, dn=None, **kwargs):
        self.dn = dn
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

    @classmethod
    def ocs_by_name(cls):
        if cls._object_class_by_name:
            return cls._object_class_by_name

        res = l.search_s("cn=subschema", ldap.SCOPE_BASE, "(objectclass=*)", ["*", "+"])
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

    def save(self):
        try:
            match = bool(l.search_s(self.dn, ldap.SCOPE_SUBTREE))
        except ldap.NO_SUCH_OBJECT:
            match = False

        if match:
            attributes = [
                (ldap.MOD_REPLACE, k, [elt.encode("utf-8") for elt in v])
                for k, v in self.attrs.items()
            ]
            l.modify_s(self.dn, attributes)

        else:
            attributes = [
                (k, [elt.encode("utf-8") for elt in v]) for k, v in self.attrs.items()
            ]
            l.add_s(self.dn, attributes)

    @classmethod
    def get(cls, dn):
        result = l.search_s(dn, ldap.SCOPE_SUBTREE)

        if not result:
            return None

        o = cls(
            dn=dn,
            **{k: [elt.decode("utf-8") for elt in v] for k, v in result[0][1].items()},
        )

        return o

    @classmethod
    def filter(cls, base=None, **kwargs):
        class_filter = "".join([f"(objectClass={oc})" for oc in cls.objectClass])
        arg_filter = "".join(f"({k}={v})" for k, v in kwargs.items())
        filter = f"(&{class_filter}{arg_filter})"
        result = l.search_s(base or cls.base, ldap.SCOPE_SUBTREE, filter)

        return [
            cls(
                dn=dn,
                **{k: [elt.decode("utf-8") for elt in v] for k, v in args.items()},
            )
            for dn, args in result
        ]

    def __getattr__(self, name):
        if (self.may and name in self.may) or (self.must and name in self.must):
            return self.attrs.get(name, [])
        return super().__getattr__(name)

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if not isinstance(value, list):
            value = [value]
        if (self.may and name in self.may) or (self.must and name in self.must):
            self.attrs[name] = value


class Client(LDAPObjectHelper):
    objectClass = ["oauthClientIdentity", "oauthClientMetadataAux"]
    base = "ou=clients,dc=mydomain,dc=tld"

    def get_client_id(self):
        return self.oauthClientID[0]

    def get_default_redirect_uri(self):
        return self.oauthRedirectURI[0]

    def get_allowed_scope(self, scope):
        return self.oauthScopeValue[0]

    def check_redirect_uri(self, redirect_uri):
        return redirect_uri in self.oauthRedirectURI

    def has_client_secret(self):
        return self.oauthClientSecret and self.oauthClientSecret[0]

    def check_client_secret(self, client_secret):
        return client_secret == self.oauthClientSecret[0]

    def check_token_endpoint_auth_method(self, method):
        return method == self.oauthTokenEndpointAuthMethod[0]

    def check_response_type(self, response_type):
        return response_type in self.oauthResponseType

    def check_grant_type(self, grant_type):
        return grant_type in self.oauthGrantType


class User(LDAPObjectHelper):
    objectClass = ["person"]
    base = "ou=users,dc=mydomain,dc=tld"


class Authorization(LDAPObjectHelper):
    objectClass = ["oauth2Authz"]
    base = "ou=authorizations,dc=mydomain,dc=tld"

    def get_redirect_uri(self):
        return Client.get(self.authzClientID[0]).oauthRedirectURI[0]

    def get_scope(self):
        return self.oauth2ScopeValue[0]


class Token(LDAPObjectHelper):
    objectClass = ["oauth2IdAccessToken"]
    base = "ou=tokens,dc=mydomain,dc=tld"

    def get_client_id(self):
        return self.authzClientID[0]

    def get_scope(self):
        return self.authzScopeValue[0]

    def get_expires_in(self):
        return self.authzAccessTokenLifetime[0]

    def get_expires_at(self):
        return self.authzAccessTokenIssueDate[0] + self.authzAccessTokenLifetime[0]


# u = User.get("cn=John Doe,ou=users,dc=mydomain,dc=tld")
# print(u.attrs)
# u = User.get("cn=Jane Doe,ou=users,dc=mydomain,dc=tld")
# print(u.attrs)

users = Client.filter()
pprint([u.attrs for u in users])
