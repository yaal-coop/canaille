import pytest

from canaille.backends.ldap.backend import Backend
from tests.backends.ldap import CustomSlapdObject


@pytest.fixture(scope="session")
def slapd_server():
    slapd = CustomSlapdObject()

    try:
        slapd.start()
        slapd.init_tree()
        for ldif in (
            "demo/ldif/memberof-config.ldif",
            "demo/ldif/ppolicy-config.ldif",
            "demo/ldif/ppolicy.ldif",
            "canaille/backends/ldap/schemas/oauth2-openldap.ldif",
            "demo/ldif/bootstrap-users-tree.ldif",
            "demo/ldif/bootstrap-oidc-tree.ldif",
        ):
            slapd.ldapadd(None, ["-f", ldif])
        yield slapd
    finally:
        slapd.stop()


@pytest.fixture
def ldap_configuration(configuration, slapd_server):
    configuration["BACKENDS"] = {
        "LDAP": {
            "ROOT_DN": slapd_server.suffix,
            "URI": slapd_server.ldap_uri,
            "BIND_DN": slapd_server.root_dn,
            "BIND_PW": slapd_server.root_pw,
            "USER_BASE": "ou=users",
            "USER_RDN": "uid",
            "USER_FILTER": "(uid={{ login }})",
            "GROUP_BASE": "ou=groups",
            "TIMEOUT": 0.1,
        },
    }
    yield configuration
    del configuration["BACKENDS"]


@pytest.fixture
def ldap_backend(slapd_server, ldap_configuration):
    backend = Backend(ldap_configuration)
    with backend.session():
        yield backend
