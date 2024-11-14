import pytest

from canaille.app.configuration import settings_factory
from canaille.backends.ldap.backend import LDAPBackend
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
            "demo/ldif/otp-config.ldif",
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
    configuration["CANAILLE_LDAP"] = {
        "ROOT_DN": slapd_server.suffix,
        "URI": slapd_server.ldap_uri,
        "BIND_DN": slapd_server.root_dn,
        "BIND_PW": slapd_server.root_pw,
        "USER_BASE": "ou=users",
        "USER_RDN": "uid",
        "USER_FILTER": "(uid={{ login }})",
        "GROUP_BASE": "ou=groups",
        "TIMEOUT": 0.1,
        "USER_CLASS": ["inetOrgPerson", "oathHOTPToken"],
    }
    yield configuration
    del configuration["CANAILLE_LDAP"]


@pytest.fixture
def ldap_backend(slapd_server, ldap_configuration):
    config_obj = settings_factory(ldap_configuration)
    config_dict = config_obj.model_dump()
    backend = LDAPBackend(config_dict)
    with backend.session():
        yield backend
