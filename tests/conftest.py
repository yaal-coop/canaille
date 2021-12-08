import datetime
import ldap.ldapobject
import os
import pytest
import slapd
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from flask_webtest import TestApp
from werkzeug.security import gen_salt
from canaille import create_app
from canaille.models import User, Client, Token, AuthorizationCode, Consent, Group
from canaille.installation import setup_ldap_tree
from canaille.ldaputils import LDAPObject


class CustomSlapdObject(slapd.Slapd):
    def __init__(self):
        super().__init__(
            schemas=(
                "core.ldif",
                "cosine.ldif",
                "nis.ldif",
                "inetorgperson.ldif",
                "schemas/oauth2-openldap.ldif",
            )
        )

    def _ln_schema_files(self, *args, **kwargs):
        dir_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "schemas"
        )
        super()._ln_schema_files(*args, **kwargs)
        super()._ln_schema_files(self.custom_schema_files, dir_path)

    def gen_config(self):
        previous = self.openldap_schema_files
        self.openldap_schema_files += self.custom_schema_files
        config = super().gen_config()
        self.openldap_schema_files = previous
        return config


@pytest.fixture(scope="session")
def keypair():
    key = rsa.generate_private_key(
        backend=crypto_default_backend(), public_exponent=65537, key_size=2048
    )
    private_key = key.private_bytes(
        crypto_serialization.Encoding.PEM,
        crypto_serialization.PrivateFormat.PKCS8,
        crypto_serialization.NoEncryption(),
    )
    public_key = key.public_key().public_bytes(
        crypto_serialization.Encoding.OpenSSH, crypto_serialization.PublicFormat.OpenSSH
    )
    return private_key, public_key


@pytest.fixture
def keypair_path(keypair, tmp_path):
    private_key, public_key = keypair

    private_key_path = os.path.join(tmp_path, "private.pem")
    with open(private_key_path, "wb") as fd:
        fd.write(private_key)

    public_key_path = os.path.join(tmp_path, "public.pem")
    with open(public_key_path, "wb") as fd:
        fd.write(public_key)

    return private_key_path, public_key_path


@pytest.fixture(scope="session")
def slapd_server():
    slapd = CustomSlapdObject()
    try:
        slapd.start()
        suffix_dc = slapd.suffix.split(",")[0][3:]
        slapd.ldapadd(
            "\n".join(
                [
                    "dn: " + slapd.suffix,
                    "objectClass: dcObject",
                    "objectClass: organization",
                    "dc: " + suffix_dc,
                    "o: " + suffix_dc,
                    "",
                    "dn: " + slapd.root_dn,
                    "objectClass: applicationProcess",
                    "cn: " + slapd.root_cn,
                    "",
                    "dn: ou=users," + slapd.suffix,
                    "objectClass: organizationalUnit",
                    "ou: users",
                    "",
                    "dn: ou=groups," + slapd.suffix,
                    "objectClass: organizationalUnit",
                    "ou: groups",
                ]
            )
            + "\n"
        )

        LDAPObject.root_dn = slapd.suffix
        User.base = "ou=users"
        Group.base = "ou=groups"

        yield slapd
    finally:
        slapd.stop()


@pytest.fixture
def slapd_connection(slapd_server):
    conn = ldap.ldapobject.SimpleLDAPObject(slapd_server.ldap_uri)
    conn.protocol_version = 3
    conn.simple_bind_s(slapd_server.root_dn, slapd_server.root_pw)
    yield conn
    conn.unbind_s()


@pytest.fixture
def configuration(slapd_server, smtpd, keypair_path):
    smtpd.config.use_starttls = True
    private_key_path, public_key_path = keypair_path
    conf = {
        "SECRET_KEY": gen_salt(24),
        "OAUTH2_METADATA_FILE": "canaille/conf/oauth-authorization-server.sample.json",
        "OIDC_METADATA_FILE": "canaille/conf/openid-configuration.sample.json",
        "LOGGING": {},
        "LDAP": {
            "ROOT_DN": slapd_server.suffix,
            "URI": slapd_server.ldap_uri,
            "BIND_DN": slapd_server.root_dn,
            "BIND_PW": slapd_server.root_pw,
            "USER_BASE": "ou=users",
            "USER_FILTER": "(|(uid={login})(cn={login}))",
            "USER_CLASS": "inetOrgPerson",
            "GROUP_BASE": "ou=groups",
            "GROUP_CLASS": "groupOfNames",
            "GROUP_NAME_ATTRIBUTE": "cn",
            "GROUP_USER_FILTER": "member={user.dn}",
            "TIMEOUT": 0.1,
        },
        "ACL": {
            "DEFAULT": {
                "READ": ["uid", "groups"],
                "PERMISSIONS": ["use_oidc"],
                "WRITE": [
                    "mail",
                    "givenName",
                    "sn",
                    "userPassword",
                    "telephoneNumber",
                    "employeeNumber",
                ],
            },
            "ADMIN": {
                "FILTER": "(|(uid=admin)(sn=admin))",
                "PERMISSIONS": [
                    "manage_users",
                    "manage_oidc",
                    "delete_account",
                    "impersonate_users",
                    "manage_groups",
                ],
                "WRITE": [
                    "groups",
                ],
            },
            "MODERATOR": {
                "FILTER": "(|(uid=moderator)(sn=moderator))",
                "PERMISSIONS": ["manage_users", "manage_groups", "delete_account"],
                "WRITE": [
                    "groups",
                ],
            },
        },
        "JWT": {
            "PUBLIC_KEY": public_key_path,
            "PRIVATE_KEY": private_key_path,
            "ALG": "RS256",
            "KTY": "RSA",
            "EXP": 3600,
            "MAPPING": {
                "SUB": "{uid}",
                "NAME": "{cn}",
                "PHONE_NUMBER": "{telephoneNumber}",
                "EMAIL": "{mail}",
                "GIVEN_NAME": "{givenName}",
                "FAMILY_NAME": "{sn}",
                "PREFERRED_USERNAME": "{displayName}",
                "LOCALE": "{preferredLanguage}",
                "PICTURE": "{jpegPhoto}",
            },
        },
        "SMTP": {
            "HOST": smtpd.hostname,
            "PORT": smtpd.port,
            "TLS": True,
            "LOGIN": smtpd.config.login_username,
            "PASSWORD": smtpd.config.login_password,
            "FROM_ADDR": "admin@mydomain.tld",
        },
    }
    return conf


@pytest.fixture
def app(configuration):
    os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "true"
    setup_ldap_tree(configuration)
    app = create_app(configuration)
    return app


@pytest.fixture
def testclient(app):
    app.config["TESTING"] = True
    return TestApp(app)


@pytest.fixture
def client(app, slapd_connection, other_client):
    c = Client(
        oauthClientID=gen_salt(24),
        oauthClientName="Some client",
        oauthClientContact="contact@mydomain.tld",
        oauthClientURI="https://mydomain.tld",
        oauthRedirectURIs=[
            "https://mydomain.tld/redirect1",
            "https://mydomain.tld/redirect2",
        ],
        oauthLogoURI="https://mydomain.tld/logo.png",
        oauthIssueDate=datetime.datetime.now(),
        oauthClientSecret=gen_salt(48),
        oauthGrantType=[
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
        ],
        oauthResponseType=["code", "token", "id_token"],
        oauthScope=["openid", "profile", "groups"],
        oauthTermsOfServiceURI="https://mydomain.tld/tos",
        oauthPolicyURI="https://mydomain.tld/policy",
        oauthJWKURI="https://mydomain.tld/jwk",
        oauthTokenEndpointAuthMethod="client_secret_basic",
    )
    c.oauthAudience = [c.dn, other_client.dn]
    c.save(slapd_connection)

    return c


@pytest.fixture
def other_client(app, slapd_connection):
    c = Client(
        oauthClientID=gen_salt(24),
        oauthClientName="Some other client",
        oauthClientContact="contact@myotherdomain.tld",
        oauthClientURI="https://myotherdomain.tld",
        oauthRedirectURIs=[
            "https://myotherdomain.tld/redirect1",
            "https://myotherdomain.tld/redirect2",
        ],
        oauthLogoURI="https://myotherdomain.tld/logo.png",
        oauthIssueDate=datetime.datetime.now(),
        oauthClientSecret=gen_salt(48),
        oauthGrantType=[
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
        ],
        oauthResponseType=["code", "token", "id_token"],
        oauthScope=["openid", "profile", "groups"],
        oauthTermsOfServiceURI="https://myotherdomain.tld/tos",
        oauthPolicyURI="https://myotherdomain.tld/policy",
        oauthJWKURI="https://myotherdomain.tld/jwk",
        oauthTokenEndpointAuthMethod="client_secret_basic",
    )
    c.oauthAudience = [c.dn]
    c.save(slapd_connection)

    return c


@pytest.fixture
def authorization(app, slapd_connection, user, client):
    a = AuthorizationCode(
        oauthCode="my-code",
        oauthClient=client.dn,
        oauthSubject=user.dn,
        oauthRedirectURI="https://foo.bar/callback",
        oauthResponseType="code",
        oauthScope="openid profile",
        oauthNonce="nonce",
        oauthAuthorizationDate=datetime.datetime(2020, 1, 1),
        oauthAuthorizationLifetime="3600",
        oauthCodeChallenge="challenge",
        oauthCodeChallengeMethod="method",
        oauthRevokation="",
    )
    a.save(slapd_connection)
    return a


@pytest.fixture
def user(app, slapd_connection):
    User.ldap_object_classes(slapd_connection)
    LDAPObject.ldap_object_attributes(slapd_connection)
    u = User(
        objectClass=["inetOrgPerson"],
        cn="John (johnny) Doe",
        sn="Doe",
        uid="user",
        mail="john@doe.com",
        userPassword="{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz",
    )
    u.save(slapd_connection)
    return u


@pytest.fixture
def admin(app, slapd_connection):
    User.ldap_object_classes(slapd_connection)
    u = User(
        objectClass=["inetOrgPerson"],
        cn="Jane Doe",
        sn="Doe",
        uid="admin",
        mail="jane@doe.com",
        userPassword="{SSHA}Vmgh2jkD0idX3eZHf8RzGos31oerjGiU",
    )
    u.save(slapd_connection)
    return u


@pytest.fixture
def moderator(app, slapd_connection):
    User.ldap_object_classes(slapd_connection)
    u = User(
        objectClass=["inetOrgPerson"],
        cn="Jack Doe",
        sn="Doe",
        uid="moderator",
        mail="jack@doe.com",
        userPassword="{SSHA}+eHyxWqajMHsOWnhONC2vbtfNZzKTkag",
    )
    u.save(slapd_connection)
    return u


@pytest.fixture
def token(slapd_connection, client, user):
    t = Token(
        oauthAccessToken=gen_salt(48),
        oauthAudience=[client.dn],
        oauthClient=client.dn,
        oauthSubject=user.dn,
        oauthTokenType=None,
        oauthRefreshToken=gen_salt(48),
        oauthScope="openid profile",
        oauthIssueDate=datetime.datetime.now(),
        oauthTokenLifetime=str(3600),
    )
    t.save(slapd_connection)
    return t


@pytest.fixture
def consent(slapd_connection, client, user):
    t = Consent(
        oauthClient=client.dn,
        oauthSubject=user.dn,
        oauthScope=["openid", "profile"],
        oauthIssueDate=datetime.datetime.now(),
    )
    t.save(slapd_connection)
    return t


@pytest.fixture
def logged_user(user, testclient):
    with testclient.session_transaction() as sess:
        sess["user_dn"] = [user.dn]
    return user


@pytest.fixture
def logged_admin(admin, testclient):
    with testclient.session_transaction() as sess:
        sess["user_dn"] = [admin.dn]
    return admin


@pytest.fixture
def logged_moderator(moderator, testclient):
    with testclient.session_transaction() as sess:
        sess["user_dn"] = [moderator.dn]
    return moderator


@pytest.fixture(autouse=True)
def cleanups(slapd_connection):
    yield
    try:
        for consent in Consent.filter(conn=slapd_connection):
            consent.delete(conn=slapd_connection)
    except Exception:
        pass


@pytest.fixture
def foo_group(app, user, slapd_connection):
    Group.ldap_object_classes(slapd_connection)
    g = Group(
        objectClass=["groupOfNames"],
        member=[user.dn],
        cn="foo",
    )
    g.save(slapd_connection)
    with app.app_context():
        user.load_groups(conn=slapd_connection)
    yield g
    user._groups = []
    g.delete(conn=slapd_connection)


@pytest.fixture
def bar_group(app, admin, slapd_connection):
    Group.ldap_object_classes(slapd_connection)
    g = Group(
        objectClass=["groupOfNames"],
        member=[admin.dn],
        cn="bar",
    )
    g.save(slapd_connection)
    with app.app_context():
        admin.load_groups(conn=slapd_connection)
    yield g
    admin._groups = []
    g.delete(conn=slapd_connection)
