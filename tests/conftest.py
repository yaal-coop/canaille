import os

import ldap.ldapobject
import pytest
import slapd
from canaille import create_app
from canaille.installation import setup_ldap_tree
from canaille.ldap_backend.ldapobject import LDAPObject
from canaille.models import Group
from canaille.models import User
from cryptography.hazmat.backends import default_backend as crypto_default_backend
from cryptography.hazmat.primitives import serialization as crypto_serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from flask_webtest import TestApp
from werkzeug.security import gen_salt


class CustomSlapdObject(slapd.Slapd):
    def __init__(self):
        super().__init__(
            schemas=(
                "core.ldif",
                "cosine.ldif",
                "nis.ldif",
                "inetorgperson.ldif",
                "canaille/ldap_backend/schemas/oauth2-openldap.ldif",
            )
        )

    def _ln_schema_files(self, *args, **kwargs):
        dir_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
            "canaille",
            "ldap_backend",
            "schemas",
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
        User.object_class = ["inetOrgPerson"]
        Group.base = "ou=groups"
        Group.object_class = ["groupOfNames"]

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
            "GROUP_BASE": "ou=groups",
            "TIMEOUT": 0.1,
        },
        "ACL": {
            "DEFAULT": {
                "READ": ["uid", "groups"],
                "PERMISSIONS": ["use_oidc"],
                "WRITE": [
                    "mail",
                    "givenName",
                    "jpegPhoto",
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
            "MAPPING": {
                "SUB": "{{ user.uid[0] }}",
                "NAME": "{{ user.cn[0] }}",
                "PHONE_NUMBER": "{{ user.telephoneNumber[0] }}",
                "EMAIL": "{{ user.mail[0] }}",
                "GIVEN_NAME": "{{ user.givenName[0] }}",
                "FAMILY_NAME": "{{ user.sn[0] }}",
                "PREFERRED_USERNAME": "{{ user.displayName[0] }}",
                "LOCALE": "{{ user.preferredLanguage[0] }}",
                "PICTURE": "{% if user.jpegPhoto %}{{ url_for('account.photo', uid=user.uid[0], field='jpegPhoto', _external=True) }}{% endif %}",
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
    LDAPObject.ldap_object_attributes(slapd_connection)
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
    LDAPObject.ldap_object_attributes(slapd_connection)
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


@pytest.fixture
def jpeg_photo():
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x01,\x01,\x00\x00\xff\xfe\x00\x13Created with GIMP\xff\xe2\x02\xb0ICC_PROFILE\x00\x01\x01\x00\x00\x02\xa0lcms\x040\x00\x00mntrRGB XYZ \x07\xe5\x00\x0c\x00\x08\x00\x0f\x00\x16\x00(acspAPPL\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf6\xd6\x00\x01\x00\x00\x00\x00\xd3-lcms\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\rdesc\x00\x00\x01 \x00\x00\x00@cprt\x00\x00\x01`\x00\x00\x006wtpt\x00\x00\x01\x98\x00\x00\x00\x14chad\x00\x00\x01\xac\x00\x00\x00,rXYZ\x00\x00\x01\xd8\x00\x00\x00\x14bXYZ\x00\x00\x01\xec\x00\x00\x00\x14gXYZ\x00\x00\x02\x00\x00\x00\x00\x14rTRC\x00\x00\x02\x14\x00\x00\x00 gTRC\x00\x00\x02\x14\x00\x00\x00 bTRC\x00\x00\x02\x14\x00\x00\x00 chrm\x00\x00\x024\x00\x00\x00$dmnd\x00\x00\x02X\x00\x00\x00$dmdd\x00\x00\x02|\x00\x00\x00$mluc\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0cenUS\x00\x00\x00$\x00\x00\x00\x1c\x00G\x00I\x00M\x00P\x00 \x00b\x00u\x00i\x00l\x00t\x00-\x00i\x00n\x00 \x00s\x00R\x00G\x00Bmluc\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0cenUS\x00\x00\x00\x1a\x00\x00\x00\x1c\x00P\x00u\x00b\x00l\x00i\x00c\x00 \x00D\x00o\x00m\x00a\x00i\x00n\x00\x00XYZ \x00\x00\x00\x00\x00\x00\xf6\xd6\x00\x01\x00\x00\x00\x00\xd3-sf32\x00\x00\x00\x00\x00\x01\x0cB\x00\x00\x05\xde\xff\xff\xf3%\x00\x00\x07\x93\x00\x00\xfd\x90\xff\xff\xfb\xa1\xff\xff\xfd\xa2\x00\x00\x03\xdc\x00\x00\xc0nXYZ \x00\x00\x00\x00\x00\x00o\xa0\x00\x008\xf5\x00\x00\x03\x90XYZ \x00\x00\x00\x00\x00\x00$\x9f\x00\x00\x0f\x84\x00\x00\xb6\xc4XYZ \x00\x00\x00\x00\x00\x00b\x97\x00\x00\xb7\x87\x00\x00\x18\xd9para\x00\x00\x00\x00\x00\x03\x00\x00\x00\x02ff\x00\x00\xf2\xa7\x00\x00\rY\x00\x00\x13\xd0\x00\x00\n[chrm\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\xa3\xd7\x00\x00T|\x00\x00L\xcd\x00\x00\x99\x9a\x00\x00&g\x00\x00\x0f\\mluc\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0cenUS\x00\x00\x00\x08\x00\x00\x00\x1c\x00G\x00I\x00M\x00Pmluc\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x0cenUS\x00\x00\x00\x08\x00\x00\x00\x1c\x00s\x00R\x00G\x00B\xff\xdb\x00C\x00\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\xff\xdb\x00C\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\xff\xc2\x00\x11\x08\x00\x01\x00\x01\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\xff\xc4\x00\x14\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x10\x03\x10\x00\x00\x01\x7f\x0f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01\x05\x02\x7f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x03\x01\x01?\x01\x7f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x02\x01\x01?\x01\x7f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x06?\x02\x7f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01?!\x7f\xff\xda\x00\x0c\x03\x01\x00\x02\x00\x03\x00\x00\x00\x10\x1f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x03\x01\x01?\x10\x7f\xff\xc4\x00\x14\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x02\x01\x01?\x10\x7f\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x01?\x10\x7f\xff\xd9"


@pytest.fixture(autouse=True)
def cleanup_users_and_groups(slapd_connection):
    yield
    User.ldap_object_classes(slapd_connection)
    Group.ldap_object_classes(slapd_connection)
    for user in User.all(conn=slapd_connection):
        user.delete(conn=slapd_connection)
    for group in Group.all(conn=slapd_connection):
        group.delete(conn=slapd_connection)
