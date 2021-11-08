import pytest
from canaille.commands import cli
from canaille import create_app
from flask_webtest import TestApp
from tests.conftest import CustomSlapdObject


@pytest.fixture(scope="module")
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

        #        LDAPObject.root_dn = slapd.suffix

        yield slapd
    finally:
        slapd.stop()


def test_setup_ldap_tree(slapd_server, configuration):
    output = slapd_server.slapcat().stdout.decode("utf-8")
    assert "dn: ou=tokens,ou=oauth,dc=slapd-test,dc=python-ldap,dc=org" not in output
    testclient = TestApp(create_app(configuration))
    runner = testclient.app.test_cli_runner()
    runner.invoke(cli, ["install"])

    output = slapd_server.slapcat().stdout.decode("utf-8")
    assert "dn: ou=tokens,ou=oauth,dc=slapd-test,dc=python-ldap,dc=org" in output
