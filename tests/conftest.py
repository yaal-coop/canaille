import datetime
import ldap.ldapobject
import os
import pytest
import slapdtest
from flask_webtest import TestApp
from werkzeug.security import gen_salt
from web import create_app
from web.models import User, Client, Token, AuthorizationCode
from web.ldaputils import LDAPObjectHelper


class CustomSlapdObject(slapdtest.SlapdObject):
    custom_schema_files = ("oauth2-openldap.schema",)

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
                ]
            )
            + "\n"
        )

        conn = ldap.ldapobject.SimpleLDAPObject(slapd.ldap_uri)
        conn.simple_bind_s(slapd.root_dn, slapd.root_pw)
        LDAPObjectHelper.root_dn = slapd.suffix
        Client.initialize(conn)
        User.initialize(conn)
        Token.initialize(conn)
        AuthorizationCode.initialize(conn)
        conn.unbind_s()

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
def app(slapd_server):
    os.environ["AUTHLIB_INSECURE_TRANSPORT"] = "true"

    app = create_app(
        {
            "SECRET_KEY": gen_salt(24),
            "OAUTH2_METADATA_FILE": "conf/oauth-authorization-server.sample.json",
            "OIDC_METADATA_FILE": "conf/openid-configuration.sample.json",

            "LDAP": {
                "ROOT_DN": slapd_server.suffix,
                "URI": slapd_server.ldap_uri,
                "BIND_DN": slapd_server.root_dn,
                "BIND_PW": slapd_server.root_pw,
                "USER_FILTER": "(|(uid={login})(cn={login}))",
                "ADMIN_FILTER": "uid=admin",
            },
            "JWT": {
                "KEY": "secret-key",
                "ALG": "HS256",
                "ISS": "https://mydomain.tld",
                "EXP": 3600,
                "MAPPING": {
                    "SUB": "uid",
                    "NAME": "cn",
                    "PHONE_NUMBER": "telephoneNumber",
                },
            },
        }
    )
    return app


@pytest.fixture
def testclient(app):
    app.config["TESTING"] = True
    return TestApp(app)


@pytest.fixture
def client(app, slapd_connection):
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
        oauthIssueDate=datetime.datetime.now().strftime("%Y%m%d%H%S%MZ"),
        oauthClientSecret=gen_salt(48),
        oauthGrantType=[
            "password",
            "authorization_code",
            "implicit",
            "hybrid",
            "refresh_token",
        ],
        oauthResponseType=["code", "token", "id_token"],
        oauthScope=["openid", "profile"],
        oauthTermsOfServiceURI="https://mydomain.tld/tos",
        oauthPolicyURI="https://mydomain.tld/policy",
        oauthJWKURI="https://mydomain.tld/jwk",
        oauthTokenEndpointAuthMethod="client_secret_basic",
    )
    c.save(slapd_connection)

    return c


@pytest.fixture
def authorization(app, slapd_connection):
    a = AuthorizationCode(
        oauthCode="my-code",
        oauthClientID="client-id",
        oauthSubject="user-id",
        oauthRedirectURI="https://foo.bar/callback",
        oauthResponseType="code",
        oauthScope="openid profile",
        oauthNonce="nonce",
        oauthAuthorizationDate="20200101000000Z",
        oauthAuthorizationLifetime="3600",
        oauthCodeChallenge="challenge",
        oauthCodeChallengeMethod="method",
        oauthRevoked="FALSE",
    )
    a.save(slapd_connection)
    return a


@pytest.fixture
def user(app, slapd_connection):
    u = User(
        cn="John Doe",
        sn="Doe",
        uid="user",
        userpassword="{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz",
    )
    u.save(slapd_connection)
    return u


@pytest.fixture
def admin(app, slapd_connection):
    u = User(
        cn="Jane Doe",
        sn="Doe",
        uid="admin",
        userpassword="{SSHA}Vmgh2jkD0idX3eZHf8RzGos31oerjGiU",
    )
    u.save(slapd_connection)
    return u


@pytest.fixture
def token(slapd_connection, client, user):
    t = Token(
        oauthAccessToken=gen_salt(48),
        oauthClientID=client.oauthClientID,
        oauthSubject=user.dn,
        oauthTokenType=None,
        oauthRefreshToken=gen_salt(48),
        oauthScope="openid profile",
        oauthIssueDate=datetime.datetime.now().strftime("%Y%m%d%H%M%SZ"),
        oauthTokenLifetime=str(3600),
    )
    t.save(slapd_connection)
    return t


@pytest.fixture
def logged_user(user, testclient):
    with testclient.session_transaction() as sess:
        sess["user_dn"] = user.dn
    return user


@pytest.fixture
def logged_admin(admin, testclient):
    with testclient.session_transaction() as sess:
        sess["user_dn"] = admin.dn
    return admin
