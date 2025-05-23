import pytest
from flask_webtest import TestApp

from canaille import create_app
from canaille.app.configuration import settings_factory
from canaille.app.installation import InstallationException
from canaille.backends.ldap.backend import LDAPBackend
from canaille.backends.ldap.ldapobject import LDAPObject
from canaille.commands import cli

from . import CustomSlapdObject


@pytest.fixture
def configuration(ldap_configuration):
    yield ldap_configuration


@pytest.fixture
def slapd_server():
    slapd = CustomSlapdObject()
    try:
        slapd.start()
        slapd.init_tree()
        for ldif in (
            "dev/ldif/memberof-config.ldif",
            "dev/ldif/bootstrap-users-tree.ldif",
        ):
            slapd.ldapadd(None, ["-f", ldif])

        yield slapd
    finally:
        slapd.stop()


def test_setup_ldap_tree(slapd_server, configuration):
    output = slapd_server.slapcat().stdout.decode("utf-8")
    assert "dn: ou=tokens,ou=oauth,dc=example,dc=org" not in output
    testclient = TestApp(create_app(configuration))
    cli_runner = testclient.app.test_cli_runner(catch_exceptions=False)

    res = cli_runner.invoke(cli, ["install"])
    assert res.exit_code == 0, res.stdout

    output = slapd_server.slapcat().stdout.decode("utf-8")
    assert "dn: ou=tokens,ou=oauth,dc=example,dc=org" in output


def test_install_schemas(configuration, slapd_server):
    configuration["CANAILLE_LDAP"]["ROOT_DN"] = slapd_server.suffix
    configuration["CANAILLE_LDAP"]["URI"] = slapd_server.ldap_uri
    configuration["CANAILLE_LDAP"]["BIND_DN"] = slapd_server.root_dn
    configuration["CANAILLE_LDAP"]["BIND_PW"] = slapd_server.root_pw
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()

    with LDAPBackend(config_dict).session():
        assert "oauthClient" not in LDAPObject.ldap_object_classes(force=True)

    LDAPBackend.setup_schemas(config_dict)

    with LDAPBackend(config_dict).session():
        assert "oauthClient" in LDAPObject.ldap_object_classes(force=True)


def test_install_schemas_twice(configuration, slapd_server):
    configuration["CANAILLE_LDAP"]["ROOT_DN"] = slapd_server.suffix
    configuration["CANAILLE_LDAP"]["URI"] = slapd_server.ldap_uri
    configuration["CANAILLE_LDAP"]["BIND_DN"] = slapd_server.root_dn
    configuration["CANAILLE_LDAP"]["BIND_PW"] = slapd_server.root_pw
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()

    with LDAPBackend(config_dict).session():
        assert "oauthClient" not in LDAPObject.ldap_object_classes(force=True)

    LDAPBackend.setup_schemas(config_dict)

    with LDAPBackend(config_dict).session():
        assert "oauthClient" in LDAPObject.ldap_object_classes(force=True)

    LDAPBackend.setup_schemas(config_dict)


admin_ldif = """
dn: uid=admin,ou=users,dc=example,dc=org
objectclass: top
objectclass: inetOrgPerson
cn: Jane Doe
givenName: Jane
sn: Doe
uid: admin
mail: admin@example.org
userPassword: {SSHA}7zQVLckaEc6cJEsS0ylVipvb2PAR/4tS
displayName: Jane.D
"""


def test_install_no_permissions_to_install_schemas(configuration, slapd_server):
    slapd_server.slapadd(admin_ldif)

    configuration["CANAILLE_LDAP"]["ROOT_DN"] = slapd_server.suffix
    configuration["CANAILLE_LDAP"]["URI"] = slapd_server.ldap_uri
    configuration["CANAILLE_LDAP"]["BIND_DN"] = "uid=admin,ou=users,dc=example,dc=org"
    configuration["CANAILLE_LDAP"]["BIND_PW"] = "admin"
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()

    with LDAPBackend(config_dict).session():
        assert "oauthClient" not in LDAPObject.ldap_object_classes(force=True)

        with pytest.raises(InstallationException):
            LDAPBackend.setup_schemas(config_dict)

        assert "oauthClient" not in LDAPObject.ldap_object_classes(force=True)


def test_install_schemas_command(configuration, slapd_server):
    configuration["CANAILLE_LDAP"]["ROOT_DN"] = slapd_server.suffix
    configuration["CANAILLE_LDAP"]["URI"] = slapd_server.ldap_uri
    configuration["CANAILLE_LDAP"]["BIND_DN"] = slapd_server.root_dn
    configuration["CANAILLE_LDAP"]["BIND_PW"] = slapd_server.root_pw
    config_obj = settings_factory(configuration)
    config_dict = config_obj.model_dump()

    with LDAPBackend(config_dict).session():
        assert "oauthClient" not in LDAPObject.ldap_object_classes(force=True)

    testclient = TestApp(create_app(configuration))
    cli_runner = testclient.app.test_cli_runner(catch_exceptions=False)

    res = cli_runner.invoke(cli, ["install"])
    assert res.exit_code == 0, res.stdout

    with LDAPBackend(config_dict).session():
        assert "oauthClient" in LDAPObject.ldap_object_classes(force=True)
