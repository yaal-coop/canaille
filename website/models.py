import ldap
import datetime
from flask import g
from authlib.common.encoding import json_loads, json_dumps
from authlib.oauth2.rfc6749.util import scope_to_list, list_to_scope
from authlib.oauth2.rfc6749 import (
    ClientMixin,
    TokenMixin,
    AuthorizationCodeMixin,
)
#class OAuth2Client(db.Model, ClientMixin):
#    __tablename__ = 'oauth2_client'
#
#    id = db.Column(db.Integer, primary_key=True)
#    user_id = db.Column(
#        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
#    user = db.relationship('User')
#
#    client_id = db.Column(db.String(48), index=True)
#    client_secret = db.Column(db.String(120))
#    client_id_issued_at = db.Column(db.Integer, nullable=False, default=0)
#    client_secret_expires_at = db.Column(db.Integer, nullable=False, default=0)
#    _client_metadata = db.Column('client_metadata', db.Text)
#
#    @property
#    def client_info(self):
#        """Implementation for Client Info in OAuth 2.0 Dynamic Client
#        Registration Protocol via `Section 3.2.1`_.
#        .. _`Section 3.2.1`: https://tools.ietf.org/html/rfc7591#section-3.2.1
#        """
#        return dict(
#            client_id=self.client_id,
#            client_secret=self.client_secret,
#            client_id_issued_at=self.client_id_issued_at,
#            client_secret_expires_at=self.client_secret_expires_at,
#        )
#
#    @property
#    def client_metadata(self):
#        if 'client_metadata' in self.__dict__:
#            return self.__dict__['client_metadata']
#        if self._client_metadata:
#            data = json_loads(self._client_metadata)
#            self.__dict__['client_metadata'] = data
#            return data
#        return {}
#
#    def set_client_metadata(self, value):
#        self._client_metadata = json_dumps(value)
#
#    @property
#    def redirect_uris(self):
#        return self.client_metadata.get('redirect_uris', [])
#
#    @property
#    def token_endpoint_auth_method(self):
#        return self.client_metadata.get(
#            'token_endpoint_auth_method',
#            'client_secret_basic'
#        )
#
#    @property
#    def grant_types(self):
#        return self.client_metadata.get('grant_types', [])
#
#    @property
#    def response_types(self):
#        return self.client_metadata.get('response_types', [])
#
#    @property
#    def client_name(self):
#        return self.client_metadata.get('client_name')
#
#    @property
#    def client_uri(self):
#        return self.client_metadata.get('client_uri')
#
#    @property
#    def logo_uri(self):
#        return self.client_metadata.get('logo_uri')
#
#    @property
#    def scope(self):
#        return self.client_metadata.get('scope', '')
#
#    @property
#    def contacts(self):
#        return self.client_metadata.get('contacts', [])
#
#    @property
#    def tos_uri(self):
#        return self.client_metadata.get('tos_uri')
#
#    @property
#    def policy_uri(self):
#        return self.client_metadata.get('policy_uri')
#
#    @property
#    def jwks_uri(self):
#        return self.client_metadata.get('jwks_uri')
#
#    @property
#    def jwks(self):
#        return self.client_metadata.get('jwks', [])
#
#    @property
#    def software_id(self):
#        return self.client_metadata.get('software_id')
#
#    @property
#    def software_version(self):
#        return self.client_metadata.get('software_version')
#
#    def get_client_id(self):
#        return self.client_id
#
#    def get_default_redirect_uri(self):
#        if self.redirect_uris:
#            return self.redirect_uris[0]
#
#    def get_allowed_scope(self, scope):
#        if not scope:
#            return ''
#        allowed = set(self.scope.split())
#        scopes = scope_to_list(scope)
#        return list_to_scope([s for s in scopes if s in allowed])
#
#    def check_redirect_uri(self, redirect_uri):
#        return redirect_uri in self.redirect_uris
#
#    def has_client_secret(self):
#        return bool(self.client_secret)
#
#    def check_client_secret(self, client_secret):
#        return self.client_secret == client_secret
#
#    def check_token_endpoint_auth_method(self, method):
#        return self.token_endpoint_auth_method == method
#
#    def check_response_type(self, response_type):
#        return response_type in self.response_types
#
#    def check_grant_type(self, grant_type):
#        return grant_type in self.grant_types
#
#
#class OAuth2AuthorizationCode(db.Model, AuthorizationCodeMixin):
#    __tablename__ = 'oauth2_code'
#
#    id = db.Column(db.Integer, primary_key=True)
#    user_id = db.Column(
#        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
#    user = db.relationship('User')
#
#    code = db.Column(db.String(120), unique=True, nullable=False)
#    client_id = db.Column(db.String(48))
#    redirect_uri = db.Column(db.Text, default='')
#    response_type = db.Column(db.Text, default='')
#    scope = db.Column(db.Text, default='')
#    nonce = db.Column(db.Text)
#    auth_time = db.Column(
#        db.Integer, nullable=False,
#        default=lambda: int(time.time())
#    )
#
#    code_challenge = db.Column(db.Text)
#    code_challenge_method = db.Column(db.String(48))
#
#    def is_expired(self):
#        return self.auth_time + 300 < time.time()
#
#    def get_redirect_uri(self):
#        return self.redirect_uri
#
#    def get_scope(self):
#        return self.scope
#
#    def get_auth_time(self):
#        return self.auth_time
#
#    def get_nonce(self):
#        return self.nonce
#
#
#class OAuth2Token(db.Model, TokenMixin):
#    __tablename__ = 'oauth2_token'
#
#    id = db.Column(db.Integer, primary_key=True)
#    user_id = db.Column(
#        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
#    user = db.relationship('User')
#
#    client_id = db.Column(db.String(48))
#    token_type = db.Column(db.String(40))
#    access_token = db.Column(db.String(255), unique=True, nullable=False)
#    refresh_token = db.Column(db.String(255), index=True)
#    scope = db.Column(db.Text, default='')
#    revoked = db.Column(db.Boolean, default=False)
#    issued_at = db.Column(
#        db.Integer, nullable=False, default=lambda: int(time.time())
#    )
#    expires_in = db.Column(db.Integer, nullable=False, default=0)
#
#    def is_refresh_token_active(self):
#        if self.revoked:
#            return False
#        expires_at = self.issued_at + self.expires_in * 2
#        return expires_at >= time.time()
#
#    def get_client_id(self):
#        return self.client_id
#
#    def get_scope(self):
#        return self.scope
#
#    def get_expires_in(self):
#        return self.expires_in
#
#    def get_expires_at(self):
#        return self.issued_at + self.expires_in

class LDAPObjectHelper:
    _object_class_by_name = None
    may = None
    must = None
    base = None
    id = None

    #TODO If ldap attribute is SINGLE-VALUE, do not bother with lists

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

        res = g.ldap.search_s("cn=subschema", ldap.SCOPE_BASE, "(objectclass=*)", ["*", "+"])
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
            cls(
                **{k: [elt.decode("utf-8") for elt in v] for k, v in args.items()},
            )
            for _, args in result
        ]

    def __getattr__(self, name):
        if (self.may and name in self.may) or (self.must and name in self.must):
            return self.attrs.get(name, [])
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if not isinstance(value, list):
            value = [value]
        if (self.may and name in self.may) or (self.must and name in self.must):
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
    objectClass = ["oauthClientIdentity"]
    base = "ou=clients,dc=mydomain,dc=tld"
    id = "oauthClientID"

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


class AuthorizationCode(LDAPObjectHelper, AuthorizationCodeMixin):
    objectClass = ["oauth2Authz"]
    base = "ou=authorizations,dc=mydomain,dc=tld"

    def get_redirect_uri(self):
        return Client.get(self.authzClientID[0]).oauthRedirectURI[0]

    def get_scope(self):
        return self.oauth2ScopeValue[0]


class Token(LDAPObjectHelper, TokenMixin):
    objectClass = ["oauth2IdAccessToken", "oauth2AuthzAux"]
    base = "ou=tokens,dc=mydomain,dc=tld"
    id = "authzAccessToken"

    def get_client_id(self):
        return self.authzClientID[0]

    def get_scope(self):
        return self.authzScopeValue[0]

    def get_expires_in(self):
        return int(self.authzAccessTokenLifetime[0])

    def get_expires_at(self):
        issue_date = datetime.datetime.strptime(self.authzAccessTokenIssueDate[0], "%Y%m%d%H%M%SZ")
        issue_timestamp = (issue_date - datetime.datetime(1970, 1, 1)).total_seconds()
        return issue_timestamp + int(self.authzAccessTokenLifetime[0])
