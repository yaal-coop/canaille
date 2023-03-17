import ldap.ldapobject
import pytest
import slapd
from canaille import create_app
from canaille.ldap_backend.backend import setup_ldap_models
from canaille.ldap_backend.ldapobject import LDAPObject
from canaille.models import Group
from canaille.models import User
from canaille.oidc.installation import setup_ldap_tree
from flask import g
from flask_webtest import TestApp
from werkzeug.security import gen_salt


class CustomSlapdObject(slapd.Slapd):
    def __init__(self):
        super().__init__(
            suffix="dc=mydomain,dc=tld",
            schemas=(
                "core.ldif",
                "cosine.ldif",
                "nis.ldif",
                "inetorgperson.ldif",
            ),
        )

    def init_tree(self):
        suffix_dc = self.suffix.split(",")[0][3:]
        self.ldapadd(
            "\n".join(
                [
                    "dn: " + self.suffix,
                    "objectClass: dcObject",
                    "objectClass: organization",
                    "dc: " + suffix_dc,
                    "o: " + suffix_dc,
                    "",
                    "dn: " + self.root_dn,
                    "objectClass: applicationProcess",
                    "cn: " + self.root_cn,
                ]
            )
            + "\n"
        )


@pytest.fixture(scope="session")
def slapd_server():
    slapd = CustomSlapdObject()

    try:
        slapd.start()
        slapd.init_tree()
        for ldif in (
            "demo/ldif/memberof-config.ldif",
            "canaille/ldap_backend/schemas/oauth2-openldap.ldif",
            "demo/ldif/bootstrap-users-tree.ldif",
            "demo/ldif/bootstrap-oidc-tree.ldif",
        ):
            with open(ldif) as fd:
                slapd.ldapadd(fd.read())
        yield slapd
    finally:
        slapd.stop()


@pytest.fixture
def slapd_connection(slapd_server, testclient):
    g.ldap_connection = ldap.ldapobject.SimpleLDAPObject(slapd_server.ldap_uri)
    g.ldap_connection.protocol_version = 3
    g.ldap_connection.simple_bind_s(slapd_server.root_dn, slapd_server.root_pw)
    yield g.ldap_connection
    g.ldap_connection.unbind_s()


@pytest.fixture
def configuration(slapd_server, smtpd):
    smtpd.config.use_starttls = True
    conf = {
        "SECRET_KEY": gen_salt(24),
        "LOGO": "/static/img/canaille-head.png",
        "LDAP": {
            "ROOT_DN": slapd_server.suffix,
            "URI": slapd_server.ldap_uri,
            "BIND_DN": slapd_server.root_dn,
            "BIND_PW": slapd_server.root_pw,
            "USER_BASE": "ou=users",
            "USER_FILTER": "(|(uid={login})(cn={login}))",
            "GROUP_BASE": "ou=groups",
            "TIMEOUT": 0.1,
        },
        "ACL": {
            "DEFAULT": {
                "READ": ["uid", "groups"],
                "PERMISSIONS": ["edit_self", "use_oidc"],
                "WRITE": [
                    "mail",
                    "givenName",
                    "jpegPhoto",
                    "sn",
                    "displayName",
                    "userPassword",
                    "telephoneNumber",
                    "postalAddress",
                    "street",
                    "postalCode",
                    "l",
                    "st",
                    "employeeNumber",
                    "preferredLanguage",
                    "departmentNumber",
                    "title",
                    "o",
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
    setup_ldap_models(configuration)
    setup_ldap_tree(configuration)
    app = create_app(configuration)
    return app


@pytest.fixture
def testclient(app):
    app.config["TESTING"] = True
    with app.app_context():
        yield TestApp(app)


@pytest.fixture
def user(app, slapd_connection):
    u = User(
        cn="John (johnny) Doe",
        givenName="John",
        sn="Doe",
        uid="user",
        mail="john@doe.com",
        userPassword="{SSHA}fw9DYeF/gHTHuVMepsQzVYAkffGcU8Fz",
        displayName="Johnny",
        preferredLanguage="en",
        telephoneNumber="555-000-000",
        labeledURI="https://john.example",
        postalAddress="1235, somewhere",
    )
    u.save()
    yield u
    u.delete()


@pytest.fixture
def admin(app, slapd_connection):
    u = User(
        cn="Jane Doe",
        sn="Doe",
        uid="admin",
        mail="jane@doe.com",
        userPassword="{SSHA}Vmgh2jkD0idX3eZHf8RzGos31oerjGiU",
    )
    u.save()
    yield u
    u.delete()


@pytest.fixture
def moderator(app, slapd_connection):
    u = User(
        cn="Jack Doe",
        sn="Doe",
        uid="moderator",
        mail="jack@doe.com",
        userPassword="{SSHA}+eHyxWqajMHsOWnhONC2vbtfNZzKTkag",
    )
    u.save()
    yield u
    u.delete()


@pytest.fixture
def logged_user(user, testclient):
    with testclient.session_transaction() as sess:
        sess["user_id"] = [user.id]
    return user


@pytest.fixture
def logged_admin(admin, testclient):
    with testclient.session_transaction() as sess:
        sess["user_id"] = [admin.id]
    return admin


@pytest.fixture
def logged_moderator(moderator, testclient):
    with testclient.session_transaction() as sess:
        sess["user_id"] = [moderator.id]
    return moderator


@pytest.fixture
def foo_group(app, user, slapd_connection):
    group = Group(
        members=[user],
        display_name="foo",
    )
    group.save()
    user.load_groups()
    yield group
    user._groups = []
    group.delete()


@pytest.fixture
def bar_group(app, admin, slapd_connection):
    group = Group(
        members=[admin],
        display_name="bar",
    )
    group.save()
    admin.load_groups()
    yield group
    admin._groups = []
    group.delete()


@pytest.fixture
def jpeg_photo():
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x01,\x01,\x00\x00\xff\xfe\x00\x13Created with GIMP\xff\xe2\x02\xb0ICC_PROFILE\x00\x01\x01\x00\x00\x02\xa0lcms\x040\x00\x00mntrRGB XYZ \x07\xe5\x00\x0c\x00\x08\x00\x0f\x00\x16\x00(acspAPPL\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf6\xd6\x00\x01\x00\x00\x00\x00\xd3-lcms\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\rdesc\x00\x00\x01 \x00\x00\x00@cprt\x00\x00\x01`\x00\x00\x006wtpt\x00\x00\x01\x98\x00\x00\x00\x14chad\x00\x00\x01\xac\x00\x00\x00,rXYZ\x00\x00\x01\xd8\x00\x00\x00\x14bXYZ\x00\x00\x01\xec\x00\x00\x00\x14gXYZ\x00\x00\x02\x00\x00\x00\x00\x14rTRC\x00\x00\x02\x14\x00\x00\x00 gTRC\x00\x00\x02\x14\x00\x00\x00 bTRC\x00\x00\x02\x14\x00\x00\x00 chrm\x00\x00\x024\x00\x00\x00$dmnd\x00\x00\x02X\x00\x00\x00$dmdd\x00\x00\x02|\x00\x00\x00$mluc\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0cenUS\x00\x00\x00$\x00\x00\x00\x1c\x00G\x00I\x00M\x00P\x00 \x00b\x00u\x00i\x00l\x00t\x00-\x00i\x00n\x00 \x00s\x00R\x00G\x00Bmluc\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0cenUS\x00\x00\x00\x1a\x00\x00\x00\x1c\x00P\x00u\x00b\x00l\x00i\x00c\x00 \x00D\x00o\x00m\x00a\x00i\x00n\x00\x00XYZ \x00\x00\x00\x00\x00\x00\xf6\xd6\x00\x01\x00\x00\x00\x00\xd3-sf32\x00\x00\x00\x00\x00\x01\x0cB\x00\x00\x05\xde\xff\xff\xf3%\x00\x00\x07\x93\x00\x00\xfd\x90\xff\xff\xfb\xa1\xff\xff\xfd\xa2\x00\x00\x03\xdc\x00\x00\xc0nXYZ \x00\x00\x00\x00\x00\x00o\xa0\x00\x008\xf5\x00\x00\x03\x90XYZ \x00\x00\x00\x00\x00\x00$\x9f\x00\x00\x0f\x84\x00\x00\xb6\xc4XYZ \x00\x00\x00\x00\x00\x00b\x97\x00\x00\xb7\x87\x00\x00\x18\xd9para\x00\x00\x00\x00\x00\x03\x00\x00\x00\x02ff\x00\x00\xf2\xa7\x00\x00\rY\x00\x00\x13\xd0\x00\x00\n[chrm\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\xa3\xd7\x00\x00T|\x00\x00L\xcd\x00\x00\x99\x9a\x00\x00&g\x00\x00\x0f\\mluc\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0cenUS\x00\x00\x00\x08\x00\x00\x00\x1c\x00G\x00I\x00M\x00Pmluc\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0cenUS\x00\x00\x00\x08\x00\x00\x00\x1c\x00s\x00R\x00G\x00B\xff\xdb\x00C\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\xff\xdb\x00C\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\xff\xc2\x00\x11\x08\x00\x01\x00\x01\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\xff\xc4\x00\x14\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x10\x03\x10\x00\x00\x01\x7f\x0f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01\x05\x02\x7f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x03\x01\x01?\x01\x7f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x02\x01\x01?\x01\x7f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x06?\x02\x7f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01?!\x7f\xff\xda\x00\x0c\x03\x01\x00\x02\x00\x03\x00\x00\x00\x10\x1f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x03\x01\x01?\x10\x7f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x02\x01\x01?\x10\x7f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01?\x10\x7f\xff\xd9"
