import os

import ldap
import pytest
from canaille import create_app
from canaille.commands import cli
from canaille.installation import setup_schemas
from canaille.ldap_backend.ldapobject import LDAPObject
from flask_webtest import TestApp
from slapd import Slapd
from tests.conftest import CustomSlapdObject


@pytest.fixture
def slapd_server_without_schemas():
    slapd = Slapd()
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

        yield slapd
    finally:
        slapd.stop()


@pytest.fixture
def configuration_without_schema(configuration, slapd_server_without_schemas):
    configuration["LDAP"]["ROOT_DN"] = slapd_server_without_schemas.suffix
    configuration["LDAP"]["URI"] = slapd_server_without_schemas.ldap_uri
    configuration["LDAP"]["BIND_DN"] = slapd_server_without_schemas.root_dn
    configuration["LDAP"]["BIND_PW"] = slapd_server_without_schemas.root_pw
    return configuration


def test_setup_ldap_tree(slapd_server_without_schemas, configuration_without_schema):
    output = slapd_server_without_schemas.slapcat().stdout.decode("utf-8")
    assert "dn: ou=tokens,ou=oauth,dc=slapd-test,dc=python-ldap,dc=org" not in output

    testclient = TestApp(create_app(configuration_without_schema, validate=False))
    runner = testclient.app.test_cli_runner()
    result = runner.invoke(cli, ["install"])

    assert not result.exception

    output = slapd_server_without_schemas.slapcat().stdout.decode("utf-8")
    assert "dn: ou=tokens,ou=oauth,dc=slapd-test,dc=python-ldap,dc=org" in output


def test_install_keypair(
    configuration_without_schema, slapd_server_without_schemas, tmpdir
):
    keys_dir = os.path.join(tmpdir, "keys")
    os.makedirs(keys_dir)
    configuration_without_schema["JWT"]["PRIVATE_KEY"] = os.path.join(
        keys_dir, "private.pem"
    )
    configuration_without_schema["JWT"]["PUBLIC_KEY"] = os.path.join(
        keys_dir, "public.pem"
    )

    assert not os.path.exists(configuration_without_schema["JWT"]["PRIVATE_KEY"])
    assert not os.path.exists(configuration_without_schema["JWT"]["PUBLIC_KEY"])

    testclient = TestApp(create_app(configuration_without_schema, validate=False))
    runner = testclient.app.test_cli_runner()
    result = runner.invoke(cli, ["install"])

    assert not result.exception

    assert os.path.exists(configuration_without_schema["JWT"]["PRIVATE_KEY"])
    assert os.path.exists(configuration_without_schema["JWT"]["PUBLIC_KEY"])


def test_install_schemas(configuration_without_schema, slapd_server_without_schemas):
    conn = ldap.ldapobject.SimpleLDAPObject(slapd_server_without_schemas.ldap_uri)
    conn.protocol_version = 3
    conn.simple_bind_s(
        slapd_server_without_schemas.root_dn, slapd_server_without_schemas.root_pw
    )

    assert "oauthClient" not in LDAPObject.ldap_object_classes(conn=conn, force=True)

    setup_schemas(configuration_without_schema)

    assert "oauthClient" in LDAPObject.ldap_object_classes(conn=conn, force=True)

    conn.unbind_s()


def test_install_schemas_command(
    configuration_without_schema, slapd_server_without_schemas
):
    conn = ldap.ldapobject.SimpleLDAPObject(slapd_server_without_schemas.ldap_uri)
    conn.protocol_version = 3
    conn.simple_bind_s(
        slapd_server_without_schemas.root_dn, slapd_server_without_schemas.root_pw
    )

    output = slapd_server_without_schemas.slapcat(["-n0"]).stdout.decode("utf-8")
    assert "oauthCode" not in output

    assert "oauthClient" not in LDAPObject.ldap_object_classes(conn=conn, force=True)

    testclient = TestApp(create_app(configuration_without_schema, validate=False))
    runner = testclient.app.test_cli_runner()
    result = runner.invoke(cli, ["install"])

    assert not result.exception

    assert "oauthClient" in LDAPObject.ldap_object_classes(conn=conn, force=True)

    conn.unbind_s()
