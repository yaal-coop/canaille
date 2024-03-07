import pytest
from canaille import create_app
from canaille.app.installation import InstallationException
from canaille.backends.ldap.backend import Backend
from canaille.backends.ldap.ldapobject import LDAPObject
from canaille.commands import cli
from flask_webtest import TestApp

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
            "demo/ldif/memberof-config.ldif",
            "demo/ldif/bootstrap-users-tree.ldif",
            "demo/ldif/bootstrap-users.ldif",
        ):
            slapd.ldapadd(None, ["-f", ldif])

        yield slapd
    finally:
        slapd.stop()


def test_setup_ldap_tree(slapd_server, configuration):
    output = slapd_server.slapcat().stdout.decode("utf-8")
    assert "dn: ou=tokens,ou=oauth,dc=mydomain,dc=tld" not in output
    testclient = TestApp(create_app(configuration, validate=False))
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["install"])
    assert res.exit_code == 0, res.stdout

    output = slapd_server.slapcat().stdout.decode("utf-8")
    assert "dn: ou=tokens,ou=oauth,dc=mydomain,dc=tld" in output


def test_install_schemas(configuration, slapd_server):
    configuration["BACKENDS"]["LDAP"]["ROOT_DN"] = slapd_server.suffix
    configuration["BACKENDS"]["LDAP"]["URI"] = slapd_server.ldap_uri
    configuration["BACKENDS"]["LDAP"]["BIND_DN"] = slapd_server.root_dn
    configuration["BACKENDS"]["LDAP"]["BIND_PW"] = slapd_server.root_pw

    with Backend(configuration).session():
        assert "oauthClient" not in LDAPObject.ldap_object_classes(force=True)

    Backend.setup_schemas(configuration)

    with Backend(configuration).session():
        assert "oauthClient" in LDAPObject.ldap_object_classes(force=True)


def test_install_schemas_twice(configuration, slapd_server):
    configuration["BACKENDS"]["LDAP"]["ROOT_DN"] = slapd_server.suffix
    configuration["BACKENDS"]["LDAP"]["URI"] = slapd_server.ldap_uri
    configuration["BACKENDS"]["LDAP"]["BIND_DN"] = slapd_server.root_dn
    configuration["BACKENDS"]["LDAP"]["BIND_PW"] = slapd_server.root_pw

    with Backend(configuration).session():
        assert "oauthClient" not in LDAPObject.ldap_object_classes(force=True)

    Backend.setup_schemas(configuration)

    with Backend(configuration).session():
        assert "oauthClient" in LDAPObject.ldap_object_classes(force=True)

    Backend.setup_schemas(configuration)


def test_install_no_permissions_to_install_schemas(configuration, slapd_server):
    configuration["BACKENDS"]["LDAP"]["ROOT_DN"] = slapd_server.suffix
    configuration["BACKENDS"]["LDAP"]["URI"] = slapd_server.ldap_uri
    configuration["BACKENDS"]["LDAP"]["BIND_DN"] = (
        "uid=admin,ou=users,dc=mydomain,dc=tld"
    )
    configuration["BACKENDS"]["LDAP"]["BIND_PW"] = "admin"

    with Backend(configuration).session():
        assert "oauthClient" not in LDAPObject.ldap_object_classes(force=True)

        with pytest.raises(InstallationException):
            Backend.setup_schemas(configuration)

        assert "oauthClient" not in LDAPObject.ldap_object_classes(force=True)


def test_install_schemas_command(configuration, slapd_server):
    configuration["BACKENDS"]["LDAP"]["ROOT_DN"] = slapd_server.suffix
    configuration["BACKENDS"]["LDAP"]["URI"] = slapd_server.ldap_uri
    configuration["BACKENDS"]["LDAP"]["BIND_DN"] = slapd_server.root_dn
    configuration["BACKENDS"]["LDAP"]["BIND_PW"] = slapd_server.root_pw

    with Backend(configuration).session():
        assert "oauthClient" not in LDAPObject.ldap_object_classes(force=True)

    testclient = TestApp(create_app(configuration, validate=False))
    runner = testclient.app.test_cli_runner()
    res = runner.invoke(cli, ["install"])
    assert res.exit_code == 0, res.stdout

    with Backend(configuration).session():
        assert "oauthClient" in LDAPObject.ldap_object_classes(force=True)
