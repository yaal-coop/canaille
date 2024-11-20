import pytest


@pytest.fixture
def configuration(ldap_configuration):
    ldap_configuration["CANAILLE_LDAP"]["USER_RDN"] = "mail"
    yield ldap_configuration


def test_user_different_rdn(testclient, slapd_server, user):
    output = slapd_server.slapcat().stdout.decode()
    assert "dn: mail=john@doe.test,ou=users,dc=mydomain,dc=tld" in output
