import os

import ldap
import pytest
from canaille import create_app
from canaille.commands import cli
from canaille.installation import InstallationException
from canaille.installation import setup_schemas
from canaille.ldap_backend.ldapobject import LDAPObject
from canaille.models import Group
from canaille.models import User
from flask_webtest import TestApp
from tests.conftest import CustomSlapdObject


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
            with open(ldif) as fd:
                slapd.ldapadd(fd.read())

        yield slapd
    finally:
        slapd.stop()


def test_setup_ldap_tree(slapd_server, configuration):
    output = slapd_server.slapcat().stdout.decode("utf-8")
    assert "dn: ou=tokens,ou=oauth,dc=mydomain,dc=tld" not in output
    testclient = TestApp(create_app(configuration, validate=False))
    runner = testclient.app.test_cli_runner()
    runner.invoke(cli, ["install"])

    output = slapd_server.slapcat().stdout.decode("utf-8")
    assert "dn: ou=tokens,ou=oauth,dc=mydomain,dc=tld" in output


def test_install_keypair(configuration, tmpdir):
    keys_dir = os.path.join(tmpdir, "keys")
    os.makedirs(keys_dir)
    configuration["JWT"]["PRIVATE_KEY"] = os.path.join(keys_dir, "private.pem")
    configuration["JWT"]["PUBLIC_KEY"] = os.path.join(keys_dir, "public.pem")

    assert not os.path.exists(configuration["JWT"]["PRIVATE_KEY"])
    assert not os.path.exists(configuration["JWT"]["PUBLIC_KEY"])

    testclient = TestApp(create_app(configuration, validate=False))
    runner = testclient.app.test_cli_runner()
    runner.invoke(cli, ["install"])

    assert os.path.exists(configuration["JWT"]["PRIVATE_KEY"])
    assert os.path.exists(configuration["JWT"]["PUBLIC_KEY"])


def test_install_schemas(configuration, slapd_server):
    configuration["LDAP"]["ROOT_DN"] = slapd_server.suffix
    configuration["LDAP"]["URI"] = slapd_server.ldap_uri
    configuration["LDAP"]["BIND_DN"] = slapd_server.root_dn
    configuration["LDAP"]["BIND_PW"] = slapd_server.root_pw

    conn = ldap.ldapobject.SimpleLDAPObject(slapd_server.ldap_uri)
    conn.protocol_version = 3
    conn.simple_bind_s(slapd_server.root_dn, slapd_server.root_pw)

    assert "oauthClient" not in LDAPObject.ldap_object_classes(conn=conn, force=True)

    setup_schemas(configuration)

    assert "oauthClient" in LDAPObject.ldap_object_classes(conn=conn, force=True)

    conn.unbind_s()
    slapd_server.stop()


def test_install_schemas_command(configuration, slapd_server):
    configuration["LDAP"]["ROOT_DN"] = slapd_server.suffix
    configuration["LDAP"]["URI"] = slapd_server.ldap_uri
    configuration["LDAP"]["BIND_DN"] = slapd_server.root_dn
    configuration["LDAP"]["BIND_PW"] = slapd_server.root_pw

    conn = ldap.ldapobject.SimpleLDAPObject(slapd_server.ldap_uri)
    conn.protocol_version = 3
    conn.simple_bind_s(slapd_server.root_dn, slapd_server.root_pw)

    assert "oauthClient" not in LDAPObject.ldap_object_classes(conn=conn, force=True)

    testclient = TestApp(create_app(configuration, validate=False))
    runner = testclient.app.test_cli_runner()
    runner.invoke(cli, ["install"])

    assert "oauthClient" in LDAPObject.ldap_object_classes(conn=conn, force=True)

    conn.unbind_s()
    slapd_server.stop()
