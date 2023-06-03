import pytest
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
            with open(ldif) as fd:
                slapd.ldapadd(fd.read())
        yield slapd
    finally:
        slapd.stop()
