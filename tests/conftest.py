import pytest
import slapd
from canaille import create_app
from canaille.app import models
from canaille.backends.ldap.backend import LDAPBackend
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
            "canaille/backends/ldap/schemas/oauth2-openldap.ldif",
            "demo/ldif/bootstrap-users-tree.ldif",
            "demo/ldif/bootstrap-oidc-tree.ldif",
        ):
            with open(ldif) as fd:
                slapd.ldapadd(fd.read())
        yield slapd
    finally:
        slapd.stop()


@pytest.fixture
def configuration(slapd_server, smtpd):
    smtpd.config.use_starttls = True
    conf = {
        "SECRET_KEY": gen_salt(24),
        "LOGO": "/static/img/canaille-head.png",
        "BACKENDS": {
            "LDAP": {
                "ROOT_DN": slapd_server.suffix,
                "URI": slapd_server.ldap_uri,
                "BIND_DN": slapd_server.root_dn,
                "BIND_PW": slapd_server.root_pw,
                "USER_BASE": "ou=users",
                "USER_FILTER": "(uid={login})",
                "GROUP_BASE": "ou=groups",
                "TIMEOUT": 0.1,
            },
        },
        "ACL": {
            "DEFAULT": {
                "READ": ["user_name", "groups"],
                "PERMISSIONS": ["edit_self", "use_oidc"],
                "WRITE": [
                    "email",
                    "given_name",
                    "photo",
                    "family_name",
                    "display_name",
                    "password",
                    "phone_number",
                    "formatted_address",
                    "street",
                    "postal_code",
                    "locality",
                    "region",
                    "employee_number",
                    "department",
                    "preferred_language",
                    "title",
                    "organization",
                ],
            },
            "ADMIN": {
                "FILTER": [{"user_name": "admin"}, {"family_name": "admin"}],
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
                "FILTER": [{"user_name": "moderator"}, {"family_name": "moderator"}],
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
def backend(slapd_server, configuration):
    backend = LDAPBackend(configuration)
    with backend.session():
        yield backend


@pytest.fixture
def app(configuration, backend):
    return create_app(configuration, backend=backend)


@pytest.fixture
def testclient(app):
    app.config["TESTING"] = True
    with app.app_context():
        yield TestApp(app)


@pytest.fixture
def user(app, backend):
    u = models.User(
        formatted_name="John (johnny) Doe",
        given_name="John",
        family_name="Doe",
        user_name="user",
        email="john@doe.com",
        password="correct horse battery staple",
        display_name="Johnny",
        preferred_language="en",
        phone_number="555-000-000",
        profile_url="https://john.example",
        formatted_address="1235, somewhere",
    )
    u.save()
    yield u
    u.delete()


@pytest.fixture
def admin(app, backend):
    u = models.User(
        formatted_name="Jane Doe",
        family_name="Doe",
        user_name="admin",
        email="jane@doe.com",
        password="admin",
    )
    u.save()
    yield u
    u.delete()


@pytest.fixture
def moderator(app, backend):
    u = models.User(
        formatted_name="Jack Doe",
        family_name="Doe",
        user_name="moderator",
        email="jack@doe.com",
        password="moderator",
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
def foo_group(app, user, backend):
    group = models.Group(
        members=[user],
        display_name="foo",
    )
    group.save()
    user.reload()
    yield group
    group.delete()


@pytest.fixture
def bar_group(app, admin, backend):
    group = models.Group(
        members=[admin],
        display_name="bar",
    )
    group.save()
    admin.reload()
    yield group
    group.delete()


@pytest.fixture
def jpeg_photo():
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x01,\x01,\x00\x00\xff\xfe\x00\x13Created with GIMP\xff\xe2\x02\xb0ICC_PROFILE\x00\x01\x01\x00\x00\x02\xa0lcms\x040\x00\x00mntrRGB XYZ \x07\xe5\x00\x0c\x00\x08\x00\x0f\x00\x16\x00(acspAPPL\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf6\xd6\x00\x01\x00\x00\x00\x00\xd3-lcms\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\rdesc\x00\x00\x01 \x00\x00\x00@cprt\x00\x00\x01`\x00\x00\x006wtpt\x00\x00\x01\x98\x00\x00\x00\x14chad\x00\x00\x01\xac\x00\x00\x00,rXYZ\x00\x00\x01\xd8\x00\x00\x00\x14bXYZ\x00\x00\x01\xec\x00\x00\x00\x14gXYZ\x00\x00\x02\x00\x00\x00\x00\x14rTRC\x00\x00\x02\x14\x00\x00\x00 gTRC\x00\x00\x02\x14\x00\x00\x00 bTRC\x00\x00\x02\x14\x00\x00\x00 chrm\x00\x00\x024\x00\x00\x00$dmnd\x00\x00\x02X\x00\x00\x00$dmdd\x00\x00\x02|\x00\x00\x00$mluc\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0cenUS\x00\x00\x00$\x00\x00\x00\x1c\x00G\x00I\x00M\x00P\x00 \x00b\x00u\x00i\x00l\x00t\x00-\x00i\x00n\x00 \x00s\x00R\x00G\x00Bmluc\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0cenUS\x00\x00\x00\x1a\x00\x00\x00\x1c\x00P\x00u\x00b\x00l\x00i\x00c\x00 \x00D\x00o\x00m\x00a\x00i\x00n\x00\x00XYZ \x00\x00\x00\x00\x00\x00\xf6\xd6\x00\x01\x00\x00\x00\x00\xd3-sf32\x00\x00\x00\x00\x00\x01\x0cB\x00\x00\x05\xde\xff\xff\xf3%\x00\x00\x07\x93\x00\x00\xfd\x90\xff\xff\xfb\xa1\xff\xff\xfd\xa2\x00\x00\x03\xdc\x00\x00\xc0nXYZ \x00\x00\x00\x00\x00\x00o\xa0\x00\x008\xf5\x00\x00\x03\x90XYZ \x00\x00\x00\x00\x00\x00$\x9f\x00\x00\x0f\x84\x00\x00\xb6\xc4XYZ \x00\x00\x00\x00\x00\x00b\x97\x00\x00\xb7\x87\x00\x00\x18\xd9para\x00\x00\x00\x00\x00\x03\x00\x00\x00\x02ff\x00\x00\xf2\xa7\x00\x00\rY\x00\x00\x13\xd0\x00\x00\n[chrm\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\xa3\xd7\x00\x00T|\x00\x00L\xcd\x00\x00\x99\x9a\x00\x00&g\x00\x00\x0f\\mluc\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0cenUS\x00\x00\x00\x08\x00\x00\x00\x1c\x00G\x00I\x00M\x00Pmluc\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0cenUS\x00\x00\x00\x08\x00\x00\x00\x1c\x00s\x00R\x00G\x00B\xff\xdb\x00C\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\xff\xdb\x00C\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\xff\xc2\x00\x11\x08\x00\x01\x00\x01\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\xff\xc4\x00\x14\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x10\x03\x10\x00\x00\x01\x7f\x0f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01\x05\x02\x7f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x03\x01\x01?\x01\x7f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x02\x01\x01?\x01\x7f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x06?\x02\x7f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01?!\x7f\xff\xda\x00\x0c\x03\x01\x00\x02\x00\x03\x00\x00\x00\x10\x1f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x03\x01\x01?\x10\x7f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x02\x01\x01?\x10\x7f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01?\x10\x7f\xff\xd9"
